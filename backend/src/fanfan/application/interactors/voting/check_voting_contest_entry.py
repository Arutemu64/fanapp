from pydantic import BaseModel

from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.user_flags import UserFlagGateway
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.constants.flags import VOTING_CONTEST_FLAG_NAME
from fanfan.core.models.user_flag import UserFlag
from fanfan.core.vo.user import UserId
from fanfan.core.vo.user_flag import generate_user_flag_id


class CheckVotingContestEntryInput(BaseModel):
    user_id: UserId


class CheckVotingContestEntry:
    def __init__(
        self,
        vote_gateway: VoteGateway,
        nomination_gateway: NominationGateway,
        user_flag_gateway: UserFlagGateway,
        uow: UnitOfWork,
    ):
        self.vote_gateway = vote_gateway
        self.nomination_gateway = nomination_gateway
        self.user_flag_gateway = user_flag_gateway
        self.uow = uow

    async def __call__(self, data: CheckVotingContestEntryInput) -> None:
        # Get count of current user votes and total votable nominations
        user_votes_count = await self.vote_gateway.count_user_votes(data.user_id)
        votable_nominations_count = await self.nomination_gateway.count_votable()

        # Check existing user flag
        flag = await self.user_flag_gateway.get_by_user(
            user_id=data.user_id, flag_name=VOTING_CONTEST_FLAG_NAME
        )

        # If it exists, let's check if it's still valid
        # If it's not - check if we can create it
        if flag and user_votes_count < votable_nominations_count:
            await self.user_flag_gateway.delete(flag)
            await self.uow.commit()
        else:
            if user_votes_count >= votable_nominations_count:
                flag = UserFlag(
                    id=generate_user_flag_id(),
                    name=VOTING_CONTEST_FLAG_NAME,
                    user_id=data.user_id,
                )
                await self.user_flag_gateway.add(flag)
                await self.uow.commit()
