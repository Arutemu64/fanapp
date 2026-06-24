from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.social_identity import SocialIdentityId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SocialIdentity(AggregateRoot):
    id: SocialIdentityId
    user_id: UserId
    provider: str
    provider_id: str
