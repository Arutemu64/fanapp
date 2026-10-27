from pydantic import BaseModel

from fanfan.application.dto.user import UserBaseDTO
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class DrawVotingContestWinnerOutput(BaseModel):
    winner: UserBaseDTO | None
    pool_size: int


class DrawVotingContestWinner:
    """Pick one random user from the voting-contest pool (everyone who voted in
    every votable nomination). Stateless: each call draws afresh and may repeat a
    previous winner, matching a live on-stage draw."""

    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> DrawVotingContestWinnerOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.VOTING_MANAGE
        )

        winner, pool_size = await self.user_gateway.draw_voting_contest_winner()

        return DrawVotingContestWinnerOutput(winner=winner, pool_size=pool_size)
