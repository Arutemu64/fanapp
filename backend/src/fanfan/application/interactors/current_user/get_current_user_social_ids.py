from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.application.ports.queries.social_ids import SocialIdentityQuery
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.services.current_user import CurrentUserProvider


class GetCurrentUserSocialIds:
    def __init__(
        self,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        social_id_query: SocialIdentityQuery,
    ) -> None:
        self.social_id_query = social_id_query
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider

    async def __call__(self) -> list[UserSocialAccountDTO]:
        current_user = await self.current_user_provider.require_user()
        return await self.social_id_query.read_user_social_accounts(current_user.id)
