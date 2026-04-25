from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.queries.social_ids import SocialIdentityQuery
from fanfan.application.ports.repositories.users import UserRepository


class GetCurrentUserSocialIds:
    def __init__(
        self,
        user_repo: UserRepository,
        id_provider: IdProvider,
        social_id_query: SocialIdentityQuery,
    ) -> None:
        self.social_id_query = social_id_query
        self.user_repo = user_repo
        self.id_provider = id_provider

    async def __call__(self) -> list[UserSocialAccountDTO]:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        return await self.social_id_query.read_user_social_accounts(current_user.id)
