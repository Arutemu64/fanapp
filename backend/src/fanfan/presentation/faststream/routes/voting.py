from dishka import FromDishka
from dishka_faststream import inject
from faststream.nats import NatsRouter, PullSub

from fanfan.application.interactors.voting.check_voting_contest_entry import (
    CheckVotingContestEntry,
    CheckVotingContestEntryInput,
)
from fanfan.core.events.voting import VoteCreated, VoteDeleted
from fanfan.presentation.faststream.jstream import stream

voting_router = NatsRouter()


@voting_router.subscriber(
    VoteCreated.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="update_contest_entry_on_new_vote",
)
@inject
async def update_contest_entry_on_new_vote(
    data: VoteCreated,
    interactor: FromDishka[CheckVotingContestEntry],
):
    await interactor(CheckVotingContestEntryInput(user_id=data.user_id))


@voting_router.subscriber(
    VoteDeleted.subject,
    stream=stream,
    pull_sub=PullSub(),
    durable="update_contest_entry_on_deleted_vote",
)
@inject
async def update_contest_entry_on_deleted_vote(
    data: VoteDeleted,
    interactor: FromDishka[CheckVotingContestEntry],
):
    await interactor(CheckVotingContestEntryInput(user_id=data.user_id))
