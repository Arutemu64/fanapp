from fanfan.adapters.db.models import UserORM
from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.user import UserId


def parse_user_ref(orm: UserORM) -> UserRefDTO:
    return UserRefDTO(id=UserId(orm.id), username=orm.username)
