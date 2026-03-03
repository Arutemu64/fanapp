from fanfan.adapters.db.models import SocialAccountORM
from fanfan.core.models.social_account import SocialAccount


class SocialAccountMapper:
    @staticmethod
    def from_model(model: SocialAccount) -> SocialAccountORM:
        return SocialAccountORM(
            id=model.id,
            user_id=model.user_id,
            provider=model.provider,
            provider_id=model.provider_id,
        )

    @staticmethod
    def to_model(orm: SocialAccountORM) -> SocialAccount:
        return SocialAccount(
            id=orm.id,
            user_id=orm.user_id,
            provider=orm.provider,
            provider_id=orm.provider_id,
        )
