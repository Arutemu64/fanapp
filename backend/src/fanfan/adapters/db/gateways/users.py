from sqlalchemy import Select, Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.mappers.user import UserMapper
from fanfan.adapters.db.models import (
    NominationORM,
    ParticipantORM,
    UserORM,
    VoteORM,
)
from fanfan.adapters.db.models.permission import UserPermissionORM
from fanfan.application.dto.page import Pagination
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserDetailsDTO,
    UserListItemDTO,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UsernameAlreadyTaken,
)
from fanfan.core.models.user import User
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId, UserRole


class SqlUserGateway(UserGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        self.mapper = UserMapper()

    def _to_model(self, user_orm: UserORM | None) -> User | None:
        if user_orm is None:
            return None
        user = self.mapper.to_model(user_orm)
        # Track the aggregate so any domain events it records are dispatched
        # by the UnitOfWork on commit.
        self.uow.register(user)
        return user

    async def add(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        with translate_integrity_error(
            {
                "ix_users_email": UserAlreadyExists,
                "ix_users_username_lower": UserAlreadyExists,
            }
        ):
            self.session.add(user_orm)
            await self.session.flush([user_orm])
        self.uow.register(user)

    async def get_by_id(self, user_id: UserId) -> User | None:
        stmt = select(UserORM).where(UserORM.id == user_id).with_for_update()
        user_orm = await self.session.scalar(stmt)
        return self._to_model(user_orm)

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(UserORM)
            .where(func.lower(UserORM.username) == username.lower())
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_model(user_orm)

    async def get_by_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        stmt = (
            select(UserORM).where(UserORM.email == normalized_email).with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_model(user_orm)

    async def save(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        with translate_integrity_error(
            {
                "ix_users_username_lower": UsernameAlreadyTaken,
                "ix_users_email": EmailAlreadyExists,
            }
        ):
            user_orm = await self.session.merge(user_orm)
            await self.session.flush([user_orm])
        self.uow.register(user)

    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(
                # ticket is many-to-one (single row) -> joinedload.
                # permissions and social_identities are independent collections;
                # joining both in one query multiplies rows (cartesian product),
                # so load each with a separate IN query instead.
                joinedload(UserORM.ticket),
                selectinload(UserORM.permissions),
                selectinload(UserORM.social_identities),
            )
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.parse_current_user_dto(user_orm) if user_orm else None

    async def read_all_by_roles(self, *roles: UserRole) -> list[UserBaseDTO]:
        stmt = select(UserORM).where(UserORM.role.in_(roles))
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]

    def _voting_contest_pool(self) -> Subquery:
        # The prize-draw pool is everyone who has voted in every votable nomination.
        # Count only votes that land in a currently-votable nomination and match the
        # number of distinct ones against the votable total: a stale vote in a
        # nomination that has since become non-votable must not stand in for a
        # missing vote in a votable one. Both the threshold and the tally come from
        # the same statement, so the pool is always internally consistent.
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

    async def count_voting_contest_pool(self) -> int:
        pool = self._voting_contest_pool()
        stmt = select(func.count()).select_from(pool)
        return await self.session.scalar(stmt) or 0

    async def read_random_voting_contest_entrant(self) -> UserBaseDTO | None:
        # ORDER BY random() LIMIT 1 draws a uniformly random entrant. The pool is
        # small (a live convention audience) and this is a one-off organiser action,
        # so the full sort scan is cheap and this is not a hot path.
        pool = self._voting_contest_pool()
        stmt = (
            select(UserORM)
            .join(pool, pool.c.user_id == UserORM.id)
            .order_by(func.random())
            .limit(1)
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.parse_base_dto(user_orm) if user_orm else None

    async def read_all_by_receive_all_announcements(self) -> list[UserBaseDTO]:
        # Bare boolean predicate (not .is_(True)) so it matches the partial
        # index ix_users_receive_all_announcements WHERE clause and can use it.
        stmt = select(UserORM).where(UserORM.receive_all_announcements)
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]

    async def read_schedule_editors(self) -> list[UserBaseDTO]:
        stmt = (
            select(UserORM)
            .join(UserPermissionORM)
            .where(UserPermissionORM.permission == Permission.SCHEDULE_MANAGE)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]

    async def read_users_page(
        self, *, pagination: Pagination, search: str | None
    ) -> list[UserListItemDTO]:
        stmt = select(UserORM)
        stmt = self._apply_user_search(stmt, search)
        # Order by username case-insensitively, with id (uuid7) as the tiebreaker
        # so rows sharing a username spelling keep a stable order across pages.
        stmt = (
            stmt.order_by(func.lower(UserORM.username), UserORM.id)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_list_item_dto(u) for u in users_orm]

    async def count_users(self, *, search: str | None) -> int:
        stmt = select(func.count(UserORM.id))
        stmt = self._apply_user_search(stmt, search)
        return await self.session.scalar(stmt) or 0

    async def read_user_details(self, user_id: UserId) -> UserDetailsDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(selectinload(UserORM.social_identities))
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.parse_details_dto(user_orm) if user_orm else None

    @staticmethod
    def _apply_user_search(stmt: Select, search: str | None) -> Select:
        # Blank query means "no filter". ILIKE gives a case-insensitive substring
        # match on username or email; %/_ in the term are escaped so a literal
        # '100%' searches for that text rather than acting as a wildcard.
        if not search or not search.strip():
            return stmt
        escaped = (
            search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        return stmt.where(
            UserORM.username.ilike(pattern) | UserORM.email.ilike(pattern)
        )
