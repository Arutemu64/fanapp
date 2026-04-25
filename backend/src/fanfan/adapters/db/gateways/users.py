from sqlalchemy import Boolean, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.social_account import SocialIdentityMapper
from fanfan.adapters.db.mappers.user import UserMapper
from fanfan.adapters.db.models import SocialIdentityORM, UserORM
from fanfan.adapters.db.models.permission import PermissionORM, UserPermissionORM
from fanfan.application.dto.user import CurrentUserDTO, UserBaseDTO
from fanfan.application.ports.queries.users import UserQuery
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UsernameAlreadyTaken,
)
from fanfan.core.models.user import User
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.user import UserId, UserRole


class SqlUserGateway(UserRepository, UserQuery):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserMapper()
        self.social_mapper = SocialIdentityMapper()

    async def add(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        try:
            self.session.add(user_orm)
            await self.session.flush([user_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name in {
                "ix_users_email",
                "ix_users_username",
                "ix_users_pending_email",
            }:
                raise UserAlreadyExists from e
            raise

    async def get_by_id(self, user_id: UserId) -> User | None:
        stmt = select(UserORM).where(UserORM.id == user_id).with_for_update()
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(UserORM)
            .where(func.lower(UserORM.username) == username.lower())
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_by_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        stmt = (
            select(UserORM).where(UserORM.email == normalized_email).with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_by_pending_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        stmt = (
            select(UserORM)
            .where(UserORM.pending_email == normalized_email)
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

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
        return self.mapper.to_model(user_orm) if user_orm else None

    async def save(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        try:
            user_orm = await self.session.merge(user_orm)
            await self.session.flush([user_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "ix_users_username":
                raise UsernameAlreadyTaken from e
            if constraint_name in {"ix_users_email", "ix_users_pending_email"}:
                raise EmailAlreadyExists from e
            raise

    async def read_current_user(self, user_id: UserId) -> CurrentUserDTO | None:
        stmt = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .options(
                joinedload(UserORM.ticket),
                joinedload(UserORM.permissions).joinedload(
                    UserPermissionORM.permission
                ),
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
            .join(PermissionORM)
            .where(PermissionORM.name == Permissions.SCHEDULE_MANAGE)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]
