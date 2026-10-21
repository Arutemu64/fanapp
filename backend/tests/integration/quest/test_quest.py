from collections.abc import Callable
from uuid import uuid7

import pytest
import pytest_asyncio
from dishka import AsyncContainer

from fanfan.application.commands.notifications import CreateNotificationCommand
from fanfan.application.dto.page import CursorPagination
from fanfan.application.interactors.quest.award_quest_points import (
    AwardQuestPoints,
    AwardQuestPointsInput,
)
from fanfan.application.interactors.quest.cancel_quest_award import CancelQuestAward
from fanfan.application.interactors.quest.find_quest_players import (
    FindQuestPlayers,
    FindQuestPlayersInput,
)
from fanfan.application.interactors.quest.get_quest import GetQuest
from fanfan.application.interactors.quest.list_quest_awards import (
    ListQuestAwards,
    ListQuestAwardsInput,
)
from fanfan.application.interactors.quest.list_quest_history import (
    ListQuestHistory,
    ListQuestHistoryInput,
)
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.quest import QuestAwardAlreadyExists, QuestDisabled
from fanfan.core.models.user import User
from fanfan.core.vo.quest import QuestAwardId
from fanfan.presentation.worker.app import routes
from tests.integration.conftest import JobsReader

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


@pytest_asyncio.fixture
async def quest_enabled(dishka_request: AsyncContainer) -> None:
    settings_gateway = await dishka_request.get(AppSettingsGateway)
    uow = await dishka_request.get(UnitOfWork)
    settings = await settings_gateway.get_for_update()
    settings.update_quest(enabled=True)
    await settings_gateway.save(settings)
    await uow.commit()


async def _award(
    dishka_request: AsyncContainer,
    player: User,
    amount: int,
    award_id: QuestAwardId | None = None,
) -> QuestAwardId:
    interactor = await dishka_request.get(AwardQuestPoints)
    result = await interactor(
        AwardQuestPointsInput(
            award_id=award_id or QuestAwardId(uuid7()),
            user_number=player.number,
            amount=amount,
            message="Задание выполнено",
        )
    )
    return result.award_id


@pytest.mark.usefixtures("quest_enabled")
async def test_awards_add_up_and_rank_the_player(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)
    await _award(dishka_request, visitor, 10)
    await _award(dishka_request, visitor, 5)

    login(visitor)
    quest = await (await dishka_request.get(GetQuest))()

    assert quest.points == 15
    assert quest.rank == 1
    assert [entry.player.id for entry in quest.leaderboard] == [visitor.id]
    assert quest.own_entry is None


@pytest.mark.usefixtures("quest_enabled")
async def test_ties_rank_whoever_reached_the_score_first(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    quest_manager: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)
    # Each award takes its own created_at from the interactor's clock, so the
    # visitor reaches 10 first. The manager's account is older, so its uuid7
    # sorts first: a ranking that fell through to the user-id tiebreaker would
    # put the manager on top and fail here.
    await _award(dishka_request, visitor, 10)
    await _award(dishka_request, quest_manager, 10)
    assert quest_manager.id < visitor.id

    login(visitor)
    quest = await (await dishka_request.get(GetQuest))()

    assert [(entry.rank, entry.player.id) for entry in quest.leaderboard] == [
        (1, visitor.id),
        (2, quest_manager.id),
    ]


@pytest.mark.usefixtures("quest_enabled")
async def test_cancelled_award_leaves_the_balance(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)
    award_id = await _award(dishka_request, visitor, 10)
    await (await dishka_request.get(CancelQuestAward))(award_id)

    page = await (await dishka_request.get(ListQuestAwards))(
        ListQuestAwardsInput(pagination=CursorPagination(limit=10))
    )
    login(visitor)
    quest = await (await dishka_request.get(GetQuest))()

    assert quest.points == 0
    assert quest.rank is None
    assert [award.can_cancel for award in page.awards] == [False]


@pytest.mark.usefixtures("quest_enabled")
async def test_award_and_cancel_each_enqueue_one_notification_for_the_player(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
    jobs: JobsReader,
) -> None:
    login(quest_volunteer)
    award_id = await _award(dishka_request, visitor, 10)
    # A replay is answered from the ledger and must not notify again.
    await _award(dishka_request, visitor, 10, award_id)
    await (await dishka_request.get(CancelQuestAward))(award_id)

    queued_jobs = await jobs()
    assert {name for name, _ in queued_jobs} == {
        task.name for task in routes[CreateNotificationCommand.subject]
    }
    titles = [message["notification"]["title"] for _, message in queued_jobs]
    assert titles == ["+10 баллов в квесте", "Начисление отменено"]
    recipients = {message["notification"]["user_id"] for _, message in queued_jobs}
    assert recipients == {str(visitor.id)}


@pytest.mark.usefixtures("quest_enabled")
async def test_history_lists_only_the_players_own_awards(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    quest_manager: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)
    first = await _award(dishka_request, visitor, 10)
    second = await _award(dishka_request, visitor, 5)
    await _award(dishka_request, quest_manager, 7)
    await (await dishka_request.get(CancelQuestAward))(first)

    login(visitor)
    history = await (await dishka_request.get(ListQuestHistory))(
        ListQuestHistoryInput(pagination=CursorPagination(limit=10))
    )

    assert [award.id for award in history.awards] == [second, first]
    assert [award.cancelled_at is None for award in history.awards] == [True, False]
    assert history.next_cursor is None


@pytest.mark.usefixtures("quest_enabled")
async def test_replayed_award_is_not_paid_twice(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)
    award_id = QuestAwardId(uuid7())
    await _award(dishka_request, visitor, 10, award_id)
    await _award(dishka_request, visitor, 10, award_id)

    with pytest.raises(QuestAwardAlreadyExists):
        await _award(dishka_request, visitor, 20, award_id)

    login(visitor)
    quest = await (await dishka_request.get(GetQuest))()
    assert quest.points == 10


@pytest.mark.usefixtures("quest_enabled")
async def test_find_players_by_username_prefix(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)

    result = await (await dishka_request.get(FindQuestPlayers))(
        FindQuestPlayersInput(search="VIS")
    )

    assert [player.id for player in result.players] == [visitor.id]


@pytest.mark.usefixtures("quest_enabled")
async def test_find_players_by_number(
    dishka_request: AsyncContainer,
    quest_volunteer: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(quest_volunteer)

    result = await (await dishka_request.get(FindQuestPlayers))(
        FindQuestPlayersInput(search=str(visitor.number))
    )

    assert [player.id for player in result.players] == [visitor.id]


@pytest.mark.usefixtures("quest_enabled")
async def test_award_needs_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
    quest_volunteer: User,
    login: Callable[[User], None],
) -> None:
    login(visitor)

    with pytest.raises(AccessDenied):
        await _award(dishka_request, quest_volunteer, 10)


async def test_quest_is_refused_while_disabled(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    login(visitor)

    with pytest.raises(QuestDisabled):
        await (await dishka_request.get(GetQuest))()
