from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.dto.vote import VoteBaseDTO
from fanfan.application.interactors.voting.add_vote import (
    AddVote,
    AddVoteInput,
    AddVoteOutput,
)
from fanfan.application.interactors.voting.cancel_vote_by_nomination import (
    CancelUserVoteByNomination,
    CancelUserVoteByNominationInput,
)
from fanfan.application.interactors.voting.get_voting_nomination import (
    GetVotingNomination,
    GetVotingNominationInput,
    GetVotingNominationOutput,
)
from fanfan.application.interactors.voting.get_voting_state import (
    GetVotingState,
    GetVotingStateOutput,
)
from fanfan.application.interactors.voting.list_voting_nominations import (
    ListVotingNominations,
    ListVotingNominationsOutput,
)
from fanfan.core.vo.nomination import NominationId
from fanfan.presentation.web.schemas.error import ErrorMessage

voting_router = APIRouter(tags=["Voting"], prefix="/voting")


@voting_router.get(
    "/status",
    status_code=200,
    summary="Get current voting state",
    description="Retrieves the current phase of the voting process "
    "(e.g., active, closed) and reasoning.",
    responses={
        200: {
            "model": GetVotingStateOutput,
            "description": "Voting status retrieved successfully.",
        },
    },
)
@inject
async def get_voting_status(
    interactor: FromDishka[GetVotingState],
) -> GetVotingStateOutput:
    return await interactor()


@voting_router.get(
    "/nominations",
    status_code=200,
    summary="List all nominations for the current vote",
    description="Retrieves a list of all candidates or items "
    "eligible for voting in the current session.",
    responses={
        200: {
            "model": ListVotingNominationsOutput,
            "description": "Nominations retrieved successfully.",
        },
    },
)
@inject
async def list_voting_nominations(
    interactor: FromDishka[ListVotingNominations],
) -> ListVotingNominationsOutput:
    return await interactor()


@voting_router.get(
    "/nominations/{nomination_code}",
    summary="Get voting nomination details",
    description="Retrieves detailed information about a specific nomination.",
    responses={
        200: {
            "model": GetVotingNominationOutput,
            "description": "Nomination details retrieved successfully.",
        },
        404: {"model": ErrorMessage, "description": "Nomination not found."},
    },
)
@inject
async def get_voting_nomination(
    nomination_code: str,
    interactor: FromDishka[GetVotingNomination],
) -> GetVotingNominationOutput:
    return await interactor(GetVotingNominationInput(nomination_code=nomination_code))


@voting_router.put(
    "/nominations/{nomination_id}/vote",
    summary="Cast a vote",
    description="Submits a vote for a participant in the specified nomination.",
    responses={
        200: {"model": VoteBaseDTO, "description": "Vote successfully cast."},
        404: {"model": ErrorMessage, "description": "Participant not found."},
        409: {
            "model": ErrorMessage,
            "description": "Already voted in this nomination.",
        },
    },
)
@inject
async def add_vote(
    nomination_id: NominationId,
    data: AddVoteInput,
    interactor: FromDishka[AddVote],
) -> AddVoteOutput:
    return await interactor(data)


@voting_router.delete(
    "/nominations/{nomination_id}/vote",
    summary="Cancel a vote",
    description="Removes a previously cast vote in the specified nomination.",
    responses={
        200: {"description": "Vote successfully cancelled."},
        404: {"model": ErrorMessage, "description": "No vote found to cancel."},
    },
)
@inject
async def cancel_vote(
    nomination_id: NominationId,
    interactor: FromDishka[CancelUserVoteByNomination],
) -> None:
    return await interactor(
        CancelUserVoteByNominationInput(nomination_id=nomination_id)
    )
