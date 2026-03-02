from adaptix import Retort
from sqlalchemy import Boolean, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.user import UserMapper
from fanfan.adapters.db.models import (
    SocialAccountORM,
    UserORM,
)
from fanfan.adapters.db.models.permission import PermissionORM, UserPermissionORM
from fanfan.core.constants.permissions import Permissions
from fanfan.core.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
)
from fanfan.core.models.social_account import SocialAccount
from fanfan.core.models.user import (
    User,
)
from fanfan.core.vo.user import UserId, UserRole

retort = Retort()


def _parse_user_base_kwargs(user: UserORM) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "role": user.role,
    }


class UserGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = UserMapper()

    async def add_user(self, user: User) -> None:
        user_orm = self.mapper.from_model(user)
        self.session.add(user_orm)

    async def add_user_social_id(self, social_identity: SocialAccount) -> SocialAccount:
        # TODO Move out
        social_id_orm = SocialAccountORM.from_model(social_identity)
        self.session.add(social_id_orm)
        await self.session.flush([social_id_orm])
        return social_id_orm.to_model()

    async def get_user_by_id(self, user_id: UserId) -> User | None:
        stmt = select(UserORM).where(UserORM.id == user_id).with_for_update()
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_user_by_username(self, username: str) -> User | None:
        stmt = (
            select(UserORM)
            .where(func.lower(UserORM.username) == username.lower())
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = (
            select(UserORM)
            .where(func.lower(UserORM.email) == email.lower())
            .with_for_update()
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_user_by_social_id(
        self, provider_name: str, provider_account_id: str
    ) -> User | None:
        stmt = (
            select(UserORM)
            .join(UserORM.social_accounts)
            .where(
                SocialAccountORM.provider == provider_name,
                SocialAccountORM.provider_id == provider_account_id,
            )
        )
        user_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(user_orm) if user_orm else None

    async def get_user_social_id_by_provider(
        self, user_id: UserId, provider: str
    ) -> SocialAccount | None:
        # TODO Move out
        stmt = select(SocialAccountORM).where(
            and_(
                SocialAccountORM.user_id == user_id,
                SocialAccountORM.provider == provider,
            )
        )
        social_id_orm = await self.session.scalar(stmt)
        return social_id_orm.to_model() if social_id_orm else None

    async def save_user(self, user: User) -> User:
        user_orm = self.mapper.from_model(user)
        user_orm = await self.session.merge(user_orm)
        await self.session.flush([user_orm])
        return self.mapper.to_model(user_orm)

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
            .where(PermissionORM.name == Permissions.CAN_MANAGE_SCHEDULE)
        )
        users_orm = await self.session.scalars(stmt)
        return [self.mapper.parse_base_dto(u) for u in users_orm]
