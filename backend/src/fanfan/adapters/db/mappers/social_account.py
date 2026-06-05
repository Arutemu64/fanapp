from fanfan.adapters.db.models import SocialIdentityORM
from fanfan.core.models.social_account import SocialIdentity


class SocialIdentityMapper:
    @staticmethod
    def from_model(model: SocialIdentity) -> SocialIdentityORM:
        return SocialIdentityORM(
            id=model.id,
            user_id=model.user_id,
            provider=model.provider,
            provider_id=model.provider_id,
        )

    @staticmethod
    def to_model(orm: SocialIdentityORM) -> SocialIdentity:
        return SocialIdentity(
            id=orm.id,
            user_id=orm.user_id,
            provider=orm.provider,
            provider_id=orm.provider_id,
        )
