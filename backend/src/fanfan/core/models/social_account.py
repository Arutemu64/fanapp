from dataclasses import dataclass, field
from uuid import UUID, uuid7

from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SocialAccount:
    id: UUID = field(default_factory=uuid7)
    user_id: UserId
    provider: str
    provider_id: str
