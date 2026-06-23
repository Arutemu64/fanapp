from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path

from fanfan.application.interactors.voting.add_vote import (
    AddVote,
    AddVoteInput,
    AddVoteOutput,
)
from fanfan.application.interactors.voting.cancel_vote import (
    CancelVote,
    CancelVoteInput,
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
from fanfan.core.vo.nomination import NominationCode
from fanfan.core.vo.vote import VoteId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import require_session_docs

voting_router = APIRouter(tags=["Voting"], prefix="/voting")


@voting_router.get(
    "/status",
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
    nomination_code: Annotated[
        NominationCode, Path(description="Voting nomination code.")
    ],
    interactor: FromDishka[GetVotingNomination],
) -> GetVotingNominationOutput:
    return await interactor(GetVotingNominationInput(nomination_code=nomination_code))


@voting_router.post(
    "/votes",
    status_code=201,
    summary="Cast a vote",
    description="Submits a vote for the given participant. "
    "The nomination is derived from the participant.",
    dependencies=[require_session_docs],
    responses={
        **AUTH_RESPONSES,
        201: {"model": AddVoteOutput, "description": "Vote successfully cast."},
        404: {"model": ErrorMessage, "description": "Participant not found."},
        409: {
            "model": ErrorMessage,
            "description": "Already voted in this nomination.",
        },
    },
)
@inject
async def add_vote(
    data: AddVoteInput,
    interactor: FromDishka[AddVote],
) -> AddVoteOutput:
    return await interactor(data)


@voting_router.delete(
    "/votes/{vote_id}",
    status_code=204,
    summary="Cancel a vote",
    description="Removes a previously cast vote by its ID.",
    dependencies=[require_session_docs],
    responses={
        **AUTH_RESPONSES,
        204: {"description": "Vote successfully cancelled."},
        404: {"model": ErrorMessage, "description": "No vote found to cancel."},
    },
)
@inject
async def cancel_vote(
    vote_id: Annotated[VoteId, Path(description="ID of the vote to cancel.")],
    interactor: FromDishka[CancelVote],
) -> None:
    await interactor(CancelVoteInput(vote_id=vote_id))
