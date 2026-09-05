from typing import cast
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import ParticipantORM, VoteORM
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import VoteAlreadyExists
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


def _from_model(model: Vote) -> VoteORM:
    return VoteORM(
        id=model.id,
        user_id=model.user_id,
        participant_id=model.participant_id,
    )


def _to_model(orm: VoteORM) -> Vote:
    return Vote(
        id=VoteId(orm.id),
        user_id=UserId(orm.user_id),
        participant_id=ParticipantId(orm.participant_id),
    )


class SqlVoteGateway(VoteGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow

    async def add(self, vote: Vote) -> None:
        vote_orm = _from_model(vote)
        # Denormalise the nomination from the participant so the DB can enforce
        # one vote per nomination; the domain Vote doesn't carry it. A missing
        # participant surfaces below as the existing FK violation (ParticipantNotFound),
        # so the None case needs no handling here — the cast just satisfies the
        # type checker, which can't see that guarantee.
        vote_orm.nomination_id = cast(
            "UUID",
            await self.session.scalar(
                select(ParticipantORM.nomination_id).where(
                    ParticipantORM.id == vote.participant_id
                )
            ),
        )
        with translate_integrity_error(
            {
                "fk_votes_participant_id_participants": ParticipantNotFound,
                "uq_votes_user_id": VoteAlreadyExists,
                "uq_votes_user_nomination": VoteAlreadyExists,
            }
        ):
            self.session.add(vote_orm)
            await self.session.flush([vote_orm])
        self.uow.register(vote)

    async def get(self, vote_id: VoteId) -> Vote | None:
        vote_orm = await self.session.scalar(
            select(VoteORM).where(VoteORM.id == vote_id).with_for_update()
        )
        if vote_orm is None:
            return None
        vote = _to_model(vote_orm)
        self.uow.register(vote)
        return vote

    async def get_user_vote_by_nomination(
        self, nomination_id: NominationId, user_id: UserId
    ) -> Vote | None:
        vote_orm = await self.session.scalar(
            select(VoteORM)
            .where(
                and_(
                    VoteORM.user_id == user_id,
                    VoteORM.nomination_id == nomination_id,
                ),
            )
            .with_for_update()
        )
        if vote_orm is None:
            return None
        vote = _to_model(vote_orm)
        self.uow.register(vote)
        return vote

    async def count_user_votes(self, user_id: UserId) -> int:
        return (
            await self.session.scalar(
                select(func.count(VoteORM.id)).where(VoteORM.user_id == user_id)
            )
            or 0
        )

    async def delete(self, vote: Vote) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.id == vote.id))
