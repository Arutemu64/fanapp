from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.voting.add_vote import AddVote, AddVoteCommand
from fanfan.application.voting.cancel_vote import CancelVote, CancelVoteRequest
from fanfan.application.voting.get_voting_nomination import (
    GetVotingNomination,
    GetVotingNominationCommand,
    GetVotingNominationResult,
)
from fanfan.application.voting.get_voting_state import (
    GetVotingState,
    GetVotingStateResult,
)
from fanfan.application.voting.list_voting_nominations import (
    ListVotingNominations,
    ListVotingNominationsResult,
)
from fanfan.core.dto.vote import VoteBaseDTO
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import AlreadyVotedInThisNomination, VoteNotFound
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
            "model": GetVotingStateResult,
            "description": "Voting status retrieved successfully.",
        },
    },
)
@inject
async def get_voting_status(
    interactor: FromDishka[GetVotingState],
) -> GetVotingStateResult:
    return await interactor()


@voting_router.get(
    "/nominations",
    status_code=200,
    summary="List all nominations for the current vote",
    description="Retrieves a list of all candidates or items "
    "eligible for voting in the current session.",
    responses={
        200: {
            "model": ListVotingNominationsResult,
            "description": "Nominations retrieved successfully.",
        },
    },
)
@inject
async def list_voting_nominations(
    interactor: FromDishka[ListVotingNominations],
) -> ListVotingNominationsResult:
    return await interactor()


@voting_router.get(
    "/nominations/{nomination_code}",
    summary="Get voting nomination details",
    description="Retrieves detailed information about a specific nomination.",
    responses={
        200: {
            "model": GetVotingNominationResult,
            "description": "Nomination details retrieved successfully.",
        },
        404: {"model": ErrorMessage, "description": "Nomination not found."},
    },
)
@inject
async def get_voting_nomination(
    nomination_code: str,
    interactor: FromDishka[GetVotingNomination],
) -> GetVotingNominationResult:
    return await interactor(GetVotingNominationCommand(nomination_code=nomination_code))


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
    data: AddVoteCommand,
    interactor: FromDishka[AddVote],
) -> VoteBaseDTO:
    try:
        return await interactor(data)
    except ParticipantNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except AlreadyVotedInThisNomination as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


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
    interactor: FromDishka[CancelVote],
) -> None:
    try:
        return await interactor(CancelVoteRequest(nomination_id=nomination_id))
    except VoteNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
