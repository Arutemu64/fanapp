from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.vote import VoteMapper
from fanfan.adapters.db.models import NominationORM, VoteORM
from fanfan.application.ports.repositories.votes import VoteRepository
from fanfan.core.exceptions.participants import ParticipantNotFound
from fanfan.core.exceptions.votes import AlreadyVotedInThisNomination
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId


class SqlVoteGateway(VoteRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = VoteMapper()

    async def add(self, vote: Vote) -> None:
        vote_orm = self.mapper.from_model(vote)
        try:
            self.session.add(vote_orm)
            await self.session.flush([vote_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "fk_votes_participant_id_participants":
                raise ParticipantNotFound from e
            if constraint_name == "uq_votes_user_id":
                raise AlreadyVotedInThisNomination from e
            raise

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
        return self.mapper.to_model(vote_orm) if vote_orm else None

    async def count_user_votes(self, user_id: UserId) -> int:
        return await self.session.scalar(
            select(func.count(VoteORM.id)).where(VoteORM.user_id == user_id)
        )

    async def delete(self, vote: Vote) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.id == vote.id))

    async def delete_all_user_votes(self, user_id: UserId) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.user_id == user_id))
