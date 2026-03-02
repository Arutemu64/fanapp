from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.vote import VoteMapper
from fanfan.adapters.db.models import NominationORM, VoteORM
from fanfan.core.dto.vote import VoteBaseDTO
from fanfan.core.models.vote import Vote
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


class VoteGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = VoteMapper()

    async def add_vote(self, vote: Vote) -> None:
        vote_orm = self.mapper.from_model(vote)
        self.session.add(vote_orm)

    async def get_vote(self, vote_id: VoteId) -> Vote | None:
        stmt = select(VoteORM).where(VoteORM.id == vote_id).with_for_update()
        vote_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(vote_orm) if vote_orm else None

    async def read_base_vote(self, vote_id: VoteId) -> VoteBaseDTO | None:
        stmt = select(VoteORM).where(VoteORM.id == vote_id)
        vote_orm = await self.session.scalar(stmt)
        return self.mapper.parse_base_dto(vote_orm) if vote_orm else None

    async def get_user_vote_by_nomination(
        self, user_id: UserId, nomination_id: NominationId
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

    async def delete_vote(self, vote: Vote) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.id == vote.id))

    async def delete_all_user_votes(self, user_id: UserId) -> None:
        await self.session.execute(delete(VoteORM).where(VoteORM.user_id == user_id))
