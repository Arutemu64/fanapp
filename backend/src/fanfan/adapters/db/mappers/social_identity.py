from fanfan.adapters.db.models import SocialIdentityORM
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialIdentityId
from fanfan.core.vo.user import UserId


class SocialIdentityMapper:
    @staticmethod
    def from_model(model: SocialIdentity) -> SocialIdentityORM:
        return SocialIdentityORM(
            id=model.id,
            user_id=model.user_id,
            provider=model.provider,
            subject=model.subject,
            provider_user_id=model.provider_user_id,
        )

    @staticmethod
    def to_model(orm: SocialIdentityORM) -> SocialIdentity:
        return SocialIdentity(
            id=SocialIdentityId(orm.id),
            user_id=UserId(orm.user_id),
            provider=orm.provider,
            subject=orm.subject,
            provider_user_id=orm.provider_user_id,
        )
