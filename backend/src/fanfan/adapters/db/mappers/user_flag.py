from fanfan.adapters.db.models import UserFlagORM
from fanfan.core.models.user_flag import UserFlag


class UserFlagMapper:
    @staticmethod
    def from_model(model: UserFlag) -> UserFlagORM:
        return UserFlagORM(
            id=model.id,
            name=model.name,
            user_id=model.user_id,
        )

    @staticmethod
    def to_model(orm: UserFlagORM) -> UserFlag:
        return UserFlag(
            id=orm.id,
            name=orm.name,
            user_id=orm.user_id,
        )
