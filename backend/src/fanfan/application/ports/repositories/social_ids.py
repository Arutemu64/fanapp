from typing import Protocol

from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.core.models.social_account import SocialIdentity
from fanfan.core.vo.user import UserId


class SocialIdentityRepository(Protocol):
    async def add(self, social_identity: SocialIdentity) -> None: ...

    async def get_by_provider(
        self,
        user_id: UserId,
        provider: str,
    ) -> SocialIdentity | None: ...

    async def delete(self, social_identity: SocialIdentity) -> None: ...

    # Read projections (return DTOs, not aggregates)
    async def read_user_social_accounts(
        self,
        user_id: UserId,
    ) -> list[UserSocialAccountDTO]: ...
