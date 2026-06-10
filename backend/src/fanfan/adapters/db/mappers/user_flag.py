from fanfan.adapters.db.models import UserFlagORM
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagId


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
            id=UserFlagId(orm.id),
            name=orm.name,
            user_id=UserId(orm.user_id),
        )
