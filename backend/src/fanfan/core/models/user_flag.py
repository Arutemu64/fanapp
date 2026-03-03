from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import UserFlagId


@dataclass(kw_only=True, slots=True)
class UserFlag:
    id: UserFlagId = field(default_factory=uuid7)
    name: str
    user_id: UserId
