from sqlalchemy import Select, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.mappers.nomination import NominationMapper
from fanfan.adapters.db.models import NominationORM, ParticipantORM, VoteORM
from fanfan.application.dto.nomination import NominationVotingDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import NominationCode
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


class SqlNominationGateway(NominationGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = NominationMapper()

    async def add(self, nomination: Nomination) -> None:
        nomination_orm = self.mapper.from_model(nomination)
        self.session.add(nomination_orm)
        await self.session.flush([nomination_orm])

    async def get_by_cosplay2_id(self, cosplay2_id: int) -> Nomination | None:
        stmt = (
            select(NominationORM)
            .where(NominationORM.cosplay2_id == cosplay2_id)
            .with_for_update()
        )
        nomination_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(nomination_orm) if nomination_orm else None

    async def count_votable(self) -> int:
        stmt = select(func.count(NominationORM.id)).where(
            NominationORM.is_votable.is_(True)
        )
        return await self.session.scalar(stmt) or 0

    async def save(self, nomination: Nomination) -> None:
        nomination_orm = await self.session.merge(self.mapper.from_model(nomination))
        await self.session.flush([nomination_orm])

    async def list_cosplay2_ids(self) -> list[int]:
        stmt = select(NominationORM.cosplay2_id)
        return list((await self.session.scalars(stmt)).all())

    async def delete_by_cosplay2_ids(self, cosplay2_ids: list[int]) -> None:
        if not cosplay2_ids:
            return
        await self.session.execute(
            delete(NominationORM).where(NominationORM.cosplay2_id.in_(cosplay2_ids))
        )

    async def read_voting_dto(
        self, nomination_code: NominationCode, user_id: UserId | None = None
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
