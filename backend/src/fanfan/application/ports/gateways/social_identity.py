from typing import Protocol

from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserId


class SocialIdentityGateway(Protocol):
    async def add(self, social_identity: SocialIdentity) -> None: ...

    async def get_by_provider(
        self,
        user_id: UserId,
        provider: SocialProvider,
    ) -> SocialIdentity | None: ...

    async def get_by_subject(
        self,
        provider: SocialProvider,
        subject: str,
    ) -> SocialIdentity | None: ...

    async def save(self, social_identity: SocialIdentity) -> None: ...

    async def delete(self, social_identity: SocialIdentity) -> None: ...
