from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagId


@dataclass(kw_only=True, slots=True)
class UserFlag(AggregateRoot):
    id: UserFlagId
    name: str
    user_id: UserId
