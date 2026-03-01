from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.voting.check_voting_contest_entry import (
    CheckVotingContestEntry,
    CheckVotingContestEntryCommand,
)
from fanfan.core.events.voting import CreatedVoteEvent, DeletedVoteEvent
from fanfan.presentation.faststream.jstream import stream

voting_router = NatsRouter()


@voting_router.subscriber(
    CreatedVoteEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="update_contest_entry_on_new_vote",
)
@inject
async def update_contest_entry_on_new_vote(
    data: CreatedVoteEvent,
    interactor: FromDishka[CheckVotingContestEntry],
):
    await interactor(CheckVotingContestEntryCommand(user_id=data.user_id))


@voting_router.subscriber(
    DeletedVoteEvent.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="update_contest_entry_on_deleted_vote",
)
@inject
async def update_contest_entry_on_deleted_vote(
    data: DeletedVoteEvent,
    interactor: FromDishka[CheckVotingContestEntry],
):
    await interactor(CheckVotingContestEntryCommand(user_id=data.user_id))
