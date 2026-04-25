from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.social_account import SocialIdentityMapper
from fanfan.adapters.db.models import SocialIdentityORM
from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.application.ports.queries.social_ids import SocialIdentityQuery
from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.core.exceptions.users import TelegramAlreadyLinkedToAnotherUser
from fanfan.core.models.social_account import SocialIdentity
from fanfan.core.vo.user import UserId


class SqlSocialIdentityGateway(SocialIdentityRepository, SocialIdentityQuery):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.social_mapper = SocialIdentityMapper()

    async def add(self, social_identity: SocialIdentity) -> None:
        social_id_orm = self.social_mapper.from_model(social_identity)
        try:
            self.session.add(social_id_orm)
            await self.session.flush([social_id_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "uq_social_accounts_provider":
                raise TelegramAlreadyLinkedToAnotherUser from e
            raise

    async def get_by_provider(
        self, user_id: UserId, provider: str
    ) -> SocialIdentity | None:
        stmt = (
            select(SocialIdentityORM)
            .where(
                and_(
                    SocialIdentityORM.user_id == user_id,
                    SocialIdentityORM.provider == provider,
                )
            )
            .with_for_update()
        )
        social_id_orm = await self.session.scalar(stmt)
        return self.social_mapper.to_model(social_id_orm) if social_id_orm else None

    async def delete(self, social_identity: SocialIdentity) -> None:
        await self.session.execute(
            delete(SocialIdentityORM).where(SocialIdentityORM.id == social_identity.id)
        )
        await self.session.flush()

    async def read_user_social_accounts(
        self, user_id: UserId
    ) -> list[UserSocialAccountDTO]:
        stmt = select(SocialIdentityORM).where(SocialIdentityORM.user_id == user_id)
        social_accounts_orm = await self.session.scalars(stmt)
        return [
            UserSocialAccountDTO(
                provider=social_account.provider,
                provider_id=social_account.provider_id,
            )
            for social_account in social_accounts_orm
        ]
