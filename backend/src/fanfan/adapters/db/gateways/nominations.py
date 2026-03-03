from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.mappers.nomination import NominationMapper
from fanfan.adapters.db.models import NominationORM, ParticipantORM, VoteORM
from fanfan.core.dto.nomination import NominationVotingDTO
from fanfan.core.dto.page import Pagination
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import NominationCode, NominationId
from fanfan.core.vo.user import UserId


def _select_nomination_voting_dto(user_id: UserId | None) -> Select:
    return (
        select(NominationORM, VoteORM)
        .outerjoin(
            VoteORM,
            and_(
                VoteORM.user_id == user_id,
                VoteORM.participant.has(
                    ParticipantORM.nomination_id == NominationORM.id
                ),
            ),
        )
        .options(undefer(NominationORM.participants_count))
    )

class NominationGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = NominationMapper()

    async def add_nomination(self, nomination: Nomination) -> Nomination:
        nomination_orm = self.mapper.from_model(nomination)
        self.session.add(nomination_orm)
        await self.session.flush([nomination_orm])
        return self.mapper.to_model(nomination_orm)

    async def get_nomination_by_id(
        self, nomination_id: NominationId
    ) -> Nomination | None:
        stmt = (
            select(NominationORM)
            .where(NominationORM.id == nomination_id)
            .with_for_update()
        )
        nomination_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(nomination_orm) if nomination_orm else None

    async def get_nomination_by_code(self, nomination_code: str) -> Nomination | None:
        stmt = (
            select(NominationORM)
            .where(NominationORM.code == nomination_code)
            .with_for_update()
        )
        nomination_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(nomination_orm) if nomination_orm else None

    async def list_nominations(
        self, pagination: Pagination | None = None
    ) -> list[Nomination]:
        stmt = select(NominationORM)

        if pagination:
            stmt = stmt.limit(pagination.limit).offset(pagination.offset)

        nominations = (await self.session.scalars(stmt)).unique()
        return [self.mapper.to_model(n) for n in nominations]

    async def count_nominations(self, is_votable: bool | None = None) -> int:
        stmt = select(func.count(NominationORM.id))
        if is_votable is not None:
            stmt = stmt.where(NominationORM.is_votable.is_(is_votable))
        return await self.session.scalar(stmt)

    async def save_nomination(self, nomination: Nomination) -> Nomination:
        nomination_orm = await self.session.merge(self.mapper.from_model(nomination))
        await self.session.flush([nomination_orm])
        return self.mapper.to_model(nomination_orm)

    async def read_nomination_by_code(
        self, nomination_code: NominationCode, user_id: UserId
    ) -> NominationVotingDTO | None:
        stmt = _select_nomination_voting_dto(user_id).where(
            NominationORM.code == nomination_code
        )

        result = (await self.session.execute(stmt)).first()

        if result:
            nomination_orm, vote_orm = result
            return self.mapper.parse_voting_dto(
                nomination_orm=nomination_orm, vote_orm=vote_orm
            )
        return None

    async def read_list_votable_nominations(
        self,
        user_id: UserId | None = None,
        pagination: Pagination | None = None,
    ) -> list[NominationVotingDTO]:
        stmt = _select_nomination_voting_dto(user_id).where(
            NominationORM.is_votable.is_(True)
        )

        if pagination:
            stmt = stmt.limit(pagination.limit).offset(pagination.offset)

        results = (await self.session.execute(stmt)).all()

        return [
            self.mapper.parse_voting_dto(
                nomination_orm=nomination_orm, vote_orm=vote_orm
            )
            for nomination_orm, vote_orm in results
        ]
