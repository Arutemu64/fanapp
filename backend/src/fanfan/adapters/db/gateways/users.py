from adaptix import Retort
from sqlalchemy import Boolean, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.mappers.social_account import SocialIdentityMapper
from fanfan.adapters.db.mappers.user import UserMapper
from fanfan.adapters.db.models import SocialIdentityORM, UserORM
from fanfan.adapters.db.models.permission import UserPermissionORM
from fanfan.application.dto.user import CurrentUserDTO, UserBaseDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UsernameAlreadyTaken,
)
from fanfan.core.models.user import User
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.user import UserId, UserRole


class SqlUserGateway(UserGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork, retort: Retort):
        self.session = session
        self.uow = uow
        self.mapper = UserMapper(retort)
        self.social_mapper = SocialIdentityMapper()

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
                "ix_users_username": UserAlreadyExists,
                "ix_users_pending_email": UserAlreadyExists,
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

    async def get_by_pending_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        stmt = (
            select(UserORM)
            .where(UserORM.pending_email == normalized_email)
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_model(user_orm)

    async def get_by_any_email(self, email: str) -> User | None:
        # Check the active address first, then the pending replacement address,
        # so conflicts stay explicit and deterministic.
        user = await self.get_by_email(email)
        if user is not None:
            return user

        return await self.get_by_pending_email(email)

    async def get_by_social_id(
        self, provider_name: str, provider_account_id: str
    ) -> User | None:
        stmt = (
            select(UserORM)
            .join(UserORM.social_accounts)
            .where(
                SocialIdentityORM.provider == provider_name,
                SocialIdentityORM.provider_id == provider_account_id,
            )
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self._to_model(user_orm)

    async def save(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        with translate_integrity_error(
            {
                "ix_users_username": UsernameAlreadyTaken,
                "ix_users_email": EmailAlreadyExists,
                "ix_users_pending_email": EmailAlreadyExists,
            }
        ):
            user_orm = await self.session.merge(user_orm)
            await self.session.flush([user_orm])
        self.uow.register(user)

    # Read projections (return DTOs, not aggregates)
    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(
                joinedload(UserORM.ticket),
                joinedload(UserORM.permissions),
            )
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.parse_current_user_dto(user_orm) if user_orm else None

    async def read_all_by_roles(self, *roles: UserRole) -> list[UserBaseDTO]:
        stmt = select(UserORM).where(UserORM.role.in_(roles))
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]

    async def read_all_by_receive_all_announcements(self) -> list[UserBaseDTO]:
        stmt = select(UserORM).where(
            cast(UserORM.settings["receive_all_announcements"].astext, Boolean)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]

    async def read_schedule_editors(self) -> list[UserBaseDTO]:
        stmt = (
            select(UserORM)
            .join(UserPermissionORM)
            .where(UserPermissionORM.permission == Permissions.SCHEDULE_MANAGE)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]
