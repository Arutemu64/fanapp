from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import SocialIdentityORM
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.core.exceptions.users import (
    SocialAccountLinkedToAnotherUser,
    UserAlreadyHasProviderLinked,
)
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialIdentityId, SocialProvider
from fanfan.core.vo.user import UserId


def _from_model(model: SocialIdentity) -> SocialIdentityORM:
    return SocialIdentityORM(
        id=model.id,
        user_id=model.user_id,
        provider=model.provider,
        subject=model.subject,
        provider_user_id=model.provider_user_id,
    )


def _to_model(orm: SocialIdentityORM) -> SocialIdentity:
    return SocialIdentity(
        id=SocialIdentityId(orm.id),
        user_id=UserId(orm.user_id),
        provider=orm.provider,
        subject=orm.subject,
        provider_user_id=orm.provider_user_id,
    )


class SqlSocialIdentityGateway(SocialIdentityGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, social_identity: SocialIdentity) -> None:
        social_identity_orm = _from_model(social_identity)
        with translate_integrity_error(
            {
                # UNIQUE(provider, subject): the external account is taken.
                "uq_social_identities_provider": SocialAccountLinkedToAnotherUser,
                # UNIQUE(user_id, provider): the user already has this provider.
                "uq_social_identities_user_id": UserAlreadyHasProviderLinked,
            }
        ):
            self.session.add(social_identity_orm)
            await self.session.flush([social_identity_orm])

    async def get_by_provider(
        self, user_id: UserId, provider: SocialProvider
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
        social_identity_orm = await self.session.scalar(stmt)
        return _to_model(social_identity_orm) if social_identity_orm else None

    async def get_by_subject(
        self, provider: SocialProvider, subject: str
    ) -> SocialIdentity | None:
        stmt = (
            select(SocialIdentityORM)
            .where(
                and_(
                    SocialIdentityORM.provider == provider,
                    SocialIdentityORM.subject == subject,
                )
            )
            .with_for_update()
        )
        social_identity_orm = await self.session.scalar(stmt)
        return _to_model(social_identity_orm) if social_identity_orm else None

    async def count_by_user(self, user_id: UserId) -> int:
        stmt = (
            select(func.count())
            .select_from(SocialIdentityORM)
            .where(SocialIdentityORM.user_id == user_id)
        )
        return await self.session.scalar(stmt) or 0

    async def delete(self, social_identity: SocialIdentity) -> None:
        await self.session.execute(
            delete(SocialIdentityORM).where(SocialIdentityORM.id == social_identity.id)
        )
        await self.session.flush()
