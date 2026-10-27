from typing import Any, override

from sqlalchemy import Select, Subquery, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from fanfan.adapters.db.constraints import (
    get_constraint_name,
    translate_integrity_error,
)
from fanfan.adapters.db.models import (
    NominationORM,
    ParticipantORM,
    TicketORM,
    UserORM,
    VoteORM,
)
from fanfan.adapters.db.models.permission import UserPermissionORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserDetailsDTO,
    UserListFilter,
    UserListItemDTO,
    UserSettingsDTO,
    UserSocialIdentityDTO,
    UserSocialLinkDTO,
    UserTicketDTO,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UsernameAlreadyTaken,
)
from fanfan.core.models.user import User, UserSettings
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.email import Email
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, Username, UserNumber, UserRole

_NUMBER_CONSTRAINT = "uq_users_number"
_NUMBER_ATTEMPTS = 5


def _from_model(model: User) -> UserORM:
    return UserORM(
        id=model.id,
        username=model.username,
        hashed_password=model.hashed_password,
        email=model.email.value if model.email else None,
        avatar_seed=model.avatar_seed,
        number=model.number,
        role=model.role,
        receive_all_announcements=model.settings.receive_all_announcements,
        receive_telegram_notifications=model.settings.receive_telegram_notifications,
        receive_vk_notifications=model.settings.receive_vk_notifications,
        settings={},
    )


def _to_model(orm: UserORM) -> User:
    return User(
        id=UserId(orm.id),
        username=Username(orm.username),
        hashed_password=orm.hashed_password,
        email=Email(orm.email) if orm.email else None,
        avatar_seed=orm.avatar_seed,
        number=UserNumber(orm.number),
        role=UserRole(orm.role),
        settings=UserSettings(
            receive_all_announcements=orm.receive_all_announcements,
            receive_telegram_notifications=orm.receive_telegram_notifications,
            receive_vk_notifications=orm.receive_vk_notifications,
        ),
    )


def _parse_base_dto(orm: UserORM) -> UserBaseDTO:
    return UserBaseDTO(
        id=UserId(orm.id),
        username=orm.username,
        role=orm.role,
    )


def _parse_list_item_dto(orm: UserORM) -> UserListItemDTO:
    return UserListItemDTO(
        id=UserId(orm.id),
        username=orm.username,
        role=orm.role,
        email=orm.email,
        avatar_seed=orm.avatar_seed,
        ticket_number=orm.ticket.barcode if orm.ticket else None,
        created_at=orm.created_at,
    )


def _parse_details_dto(orm: UserORM) -> UserDetailsDTO:
    return UserDetailsDTO(
        id=UserId(orm.id),
        username=orm.username,
        role=orm.role,
        email=orm.email,
        avatar_seed=orm.avatar_seed,
        ticket_number=orm.ticket.barcode if orm.ticket else None,
        created_at=orm.created_at,
        social_links=[
            UserSocialLinkDTO(
                provider=identity.provider,
                id=str(identity.provider_user_id),
            )
            for identity in orm.social_identities
        ],
        permissions=[Permission(p.permission) for p in orm.permissions],
    )


def _parse_current_user_dto(orm: UserORM) -> CurrentUserDTO:
    return CurrentUserDTO(
        id=UserId(orm.id),
        number=UserNumber(orm.number),
        username=orm.username,
        role=orm.role,
        email=orm.email,
        avatar_seed=orm.avatar_seed,
        has_password=bool(orm.hashed_password),
        ticket=UserTicketDTO(
            id=TicketId(orm.ticket.id),
            barcode=orm.ticket.barcode,
            role=orm.ticket.role,
        )
        if orm.ticket
        else None,
        permissions=[Permission(p.permission) for p in orm.permissions],
        settings=UserSettingsDTO(
            receive_all_announcements=orm.receive_all_announcements,
            receive_telegram_notifications=orm.receive_telegram_notifications,
            receive_vk_notifications=orm.receive_vk_notifications,
        ),
        social_identities=[
            UserSocialIdentityDTO(provider=social_identity.provider)
            for social_identity in orm.social_identities
        ],
    )


def _voting_contest_pool() -> Subquery:
    votable_count = (
        select(func.count(NominationORM.id))
        .where(NominationORM.is_votable.is_(True))
        .scalar_subquery()
    )
    return (
        select(VoteORM.user_id.label("user_id"))
        .join(ParticipantORM, VoteORM.participant_id == ParticipantORM.id)
        .join(NominationORM, ParticipantORM.nomination_id == NominationORM.id)
        .where(NominationORM.is_votable.is_(True))
        .group_by(VoteORM.user_id)
        .having(
            func.count(func.distinct(ParticipantORM.nomination_id)) >= votable_count
        )
        .subquery()
    )


class SqlUserGateway(UserGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    def _to_tracked_model(self, user_orm: UserORM | None) -> User | None:
        if user_orm is None:
            return None
        user = _to_model(user_orm)
        self.uow.register(user)
        return user

    @override
    async def add(self, user: User) -> None:
        for attempt in range(1, _NUMBER_ATTEMPTS + 1):
            try:
                await self._insert(user)
                break
            except IntegrityError as e:
                if get_constraint_name(e) != _NUMBER_CONSTRAINT:
                    raise
                if attempt == _NUMBER_ATTEMPTS:
                    raise
                user.redraw_number()
        self.uow.register(user)

    async def _insert(self, user: User) -> None:
        async with self.session.begin_nested():
            with translate_integrity_error(
                {
                    "ix_users_email": UserAlreadyExists,
                    "ix_users_username_lower": UserAlreadyExists,
                }
            ):
                self.session.add(_from_model(user))
                await self.session.flush()

    # FOR NO KEY UPDATE: it never changes users.id, and unlike FOR UPDATE it
    # lets the auth_sessions foreign-key check through while a login holds the
    # row (https://www.postgresql.org/docs/current/explicit-locking.html#LOCKING-ROWS).
    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        stmt = (
            select(UserORM).where(UserORM.id == user_id).with_for_update(key_share=True)
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_tracked_model(user_orm)

    @override
    async def get_by_number(self, number: UserNumber) -> User | None:
        stmt = (
            select(UserORM)
            .where(UserORM.number == number)
            .with_for_update(key_share=True)
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_tracked_model(user_orm)

    @override
    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(UserORM)
            .where(func.lower(UserORM.username) == username.lower())
            .with_for_update(key_share=True)
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_tracked_model(user_orm)

    @override
    async def get_by_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        stmt = (
            select(UserORM)
            .where(UserORM.email == normalized_email)
            .with_for_update(key_share=True)
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_tracked_model(user_orm)

    @override
    async def save(self, user: User) -> None:
        user_orm = _from_model(user)
        with translate_integrity_error(
            {
                "ix_users_username_lower": UsernameAlreadyTaken,
                "ix_users_email": EmailAlreadyExists,
            }
        ):
            await self.session.merge(user_orm)
            await self.session.flush()
        self.uow.register(user)

    @override
    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(
                joinedload(UserORM.ticket),
                selectinload(UserORM.permissions),
                selectinload(UserORM.social_identities),
            )
        )
        user_orm = await self.session.scalar(stmt)
        return _parse_current_user_dto(user_orm) if user_orm else None

    @override
    async def read_ids_by_roles(self, *roles: UserRole) -> list[UserId]:
        stmt = select(UserORM.id).where(UserORM.role.in_(roles))
        user_ids = await self.session.scalars(stmt)
        return [UserId(user_id) for user_id in user_ids]

    @override
    async def count_voting_contest_pool(self) -> int:
        pool = _voting_contest_pool()
        stmt = select(func.count()).select_from(pool)
        return await self.session.scalar(stmt) or 0

    @override
    async def draw_voting_contest_winner(self) -> tuple[UserBaseDTO | None, int]:
        pool = _voting_contest_pool()
        stmt = (
            select(UserORM, func.count().over().label("pool_size"))
            .join(pool, pool.c.user_id == UserORM.id)
            .order_by(func.random())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None, 0
        user_orm, pool_size = row
        return _parse_base_dto(user_orm), pool_size

    @override
    async def read_ids_receiving_all_announcements(self) -> list[UserId]:
        stmt = select(UserORM.id).where(UserORM.receive_all_announcements)
        user_ids = await self.session.scalars(stmt)
        return [UserId(user_id) for user_id in user_ids]

    @override
    async def read_schedule_editors(self) -> list[UserBaseDTO]:
        stmt = (
            select(UserORM)
            .join(UserPermissionORM)
            .where(UserPermissionORM.permission == Permission.SCHEDULE_MANAGE)
        )
        users_orm = await self.session.scalars(stmt)
        return [_parse_base_dto(u) for u in users_orm]

    @override
    async def read_users_page(
        self, *, pagination: CursorPagination, user_filter: UserListFilter
    ) -> list[UserListItemDTO]:
        stmt = select(UserORM).options(joinedload(UserORM.ticket))
        stmt = self._apply_user_filter(stmt, user_filter)
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(UserORM.created_at, UserORM.id, pagination.after)
            )
        stmt = stmt.order_by(UserORM.created_at.desc(), UserORM.id.desc()).limit(
            pagination.fetch_limit
        )
        result = await self.session.execute(stmt)
        users_orm = result.scalars().unique()
        return [_parse_list_item_dto(u) for u in users_orm]

    @override
    async def count_users(self, *, user_filter: UserListFilter) -> int:
        stmt = select(func.count(UserORM.id))
        stmt = self._apply_user_filter(stmt, user_filter)
        return await self.session.scalar(stmt) or 0

    @override
    async def read_user_details(self, user_id: UserId) -> UserDetailsDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(
                joinedload(UserORM.ticket),
                selectinload(UserORM.social_identities),
                selectinload(UserORM.permissions),
            )
        )
        user_orm = await self.session.scalar(stmt)
        return _parse_details_dto(user_orm) if user_orm else None

    @staticmethod
    def _apply_user_filter[SelectT: Select[Any]](
        stmt: SelectT, user_filter: UserListFilter
    ) -> SelectT:
        if user_filter.role is not None:
            stmt = stmt.where(UserORM.role == user_filter.role)
        if user_filter.has_ticket is True:
            stmt = stmt.where(UserORM.ticket.has())
        elif user_filter.has_ticket is False:
            stmt = stmt.where(~UserORM.ticket.has())

        search = user_filter.search
        if not search or not search.strip():
            return stmt
        escaped = (
            search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        return stmt.where(
            UserORM.username.ilike(pattern)
            | UserORM.email.ilike(pattern)
            | UserORM.ticket.has(TicketORM.barcode.ilike(pattern))
        )
