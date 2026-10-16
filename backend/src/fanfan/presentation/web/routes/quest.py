from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.quest import QuestPlayerDTO
from fanfan.application.interactors.quest.award_quest_points import (
    AwardQuestPoints,
    AwardQuestPointsInput,
    AwardQuestPointsOutput,
)
from fanfan.application.interactors.quest.cancel_quest_award import CancelQuestAward
from fanfan.application.interactors.quest.find_quest_players import (
    FindQuestPlayers,
    FindQuestPlayersInput,
    FindQuestPlayersOutput,
)
from fanfan.application.interactors.quest.get_quest import GetQuest, GetQuestOutput
from fanfan.application.interactors.quest.get_quest_player import GetQuestPlayer
from fanfan.application.interactors.quest.list_quest_awards import (
    ListQuestAwards,
    ListQuestAwardsInput,
    ListQuestAwardsOutput,
)
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.schemas.page import PageCursorQuery
from fanfan.presentation.web.security import session_security

quest_router = APIRouter(
    tags=["Quest"],
    prefix="/quest",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@quest_router.get(
    "",
    summary="Get the quest",
    description="Returns the current user's points and rank with the top of the "
    "leaderboard. Ties rank by who reached the score first.",
    responses={
        200: {"description": "Quest retrieved successfully."},
        403: {"model": ErrorMessage, "description": "The quest is disabled."},
    },
)
@inject
async def get_quest(interactor: FromDishka[GetQuest]) -> GetQuestOutput:
    return await interactor()


@quest_router.get(
    "/players",
    summary="Find quest players",
    description="Finds players whose username starts with the search term. "
    "Requires the quest:award permission.",
    responses={200: {"description": "Players found."}},
)
@inject
async def find_quest_players(
    interactor: FromDishka[FindQuestPlayers],
    search: Annotated[str, Query(min_length=1, max_length=64)],
) -> FindQuestPlayersOutput:
    return await interactor(FindQuestPlayersInput(search=search))


@quest_router.get(
    "/players/{user_id}",
    summary="Get a quest player",
    description="Returns one player's points, for the award form after a QR "
    "scan. Requires the quest:award permission.",
    responses={
        200: {"description": "Player retrieved successfully."},
        404: {"model": ErrorMessage, "description": "The user does not exist."},
    },
)
@inject
async def get_quest_player(
    user_id: UserId,
    interactor: FromDishka[GetQuestPlayer],
) -> QuestPlayerDTO:
    return await interactor(user_id)


@quest_router.post(
    "/awards",
    status_code=201,
    summary="Award quest points",
    description="Gives a player points for a quest task. Replaying the same "
    "award ID with the same payload returns the original award. Requires the "
    "quest:award permission.",
    responses={
        201: {"description": "Points awarded."},
        404: {"model": ErrorMessage, "description": "The user does not exist."},
        409: {
            "model": ErrorMessage,
            "description": "The award ID is taken by a different award.",
        },
    },
)
@inject
async def award_quest_points(
    data: AwardQuestPointsInput,
    interactor: FromDishka[AwardQuestPoints],
) -> AwardQuestPointsOutput:
    return await interactor(data)


@quest_router.get(
    "/awards",
    summary="List quest awards",
    description="Lists the awards the current user gave, newest first; holders "
    "of quest:manage see every award. Requires quest:award or quest:manage.",
    responses={200: {"description": "Awards retrieved successfully."}},
)
@inject
async def list_quest_awards(
    interactor: FromDishka[ListQuestAwards],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: PageCursorQuery = None,
) -> ListQuestAwardsOutput:
    data = ListQuestAwardsInput(
        pagination=CursorPagination.from_token(limit=limit, cursor=cursor)
    )
    return await interactor(data)


@quest_router.post(
    "/awards/{award_id}/cancel",
    status_code=204,
    summary="Cancel a quest award",
    description="Takes an award's points back. A volunteer may cancel their own "
    "award within the cancel window; quest:manage cancels any award at any time.",
    responses={
        204: {"description": "Award cancelled."},
        404: {"model": ErrorMessage, "description": "The award does not exist."},
        409: {
            "model": ErrorMessage,
            "description": "The award is already cancelled or its window expired.",
        },
    },
)
@inject
async def cancel_quest_award(
    award_id: QuestAwardId,
    interactor: FromDishka[CancelQuestAward],
) -> None:
    await interactor(award_id)
