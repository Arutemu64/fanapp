from dataclasses import dataclass

from fanfan.core.vo.social_identity import SocialIdentityId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SocialIdentity:
    id: SocialIdentityId
    user_id: UserId
    provider: str
    provider_id: str
