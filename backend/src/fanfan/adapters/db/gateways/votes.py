from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.mappers.vote import VoteMapper
from fanfan.adapters.db.models import NominationORM, VoteORM
from fanfan.application.ports.gateways.votes import VoteGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import VoteAlreadyExists
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId


class SqlVoteGateway(VoteGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork):
        self.session = session
        self.uow = uow
        self.mapper = VoteMapper()

    async def add(self, vote: Vote) -> None:
        vote_orm = self.mapper.from_model(vote)
        with translate_integrity_error(
            {
                "fk_votes_participant_id_participants": ParticipantNotFound,
                "uq_votes_user_id": VoteAlreadyExists,
            }
        ):
            self.session.add(vote_orm)
            await self.session.flush([vote_orm])
        self.uow.register(vote)

    async def get_user_vote_by_nomination(
        self, nomination_id: NominationId, user_id: UserId
    ) -> Vote | None:
        vote_orm = await self.session.scalar(
            select(VoteORM)
            .where(
                and_(
                    VoteORM.user_id == user_id,
                    VoteORM.nomination.has(NominationORM.id == nomination_id),
                ),
            )
            .with_for_update()
        )
        if vote_orm is None:
            return None
        vote = self.mapper.to_model(vote_orm)
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

    async def delete_all_user_votes(self, user_id: UserId) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.user_id == user_id))
