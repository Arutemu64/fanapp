from sqlalchemy import Select, String, and_, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.mappers.participant import ParticipantMapper
from fanfan.adapters.db.models import (
    NominationORM,
    ParticipantORM,
    VoteORM,
)
from fanfan.application.dto.page import Pagination
from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.application.ports.queries.participants import ParticipantQuery
from fanfan.application.ports.repositories.participants import ParticipantRepository
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.user import UserId


def _select_participant_dto(user_id: UserId | None) -> Select:
    return (
        select(ParticipantORM, VoteORM)
        .outerjoin(
            VoteORM,
            and_(
                VoteORM.participant_id == ParticipantORM.id,
                VoteORM.user_id == user_id,
            ),
        )
        .options(undefer(ParticipantORM.votes_count))
    )


def _filter_participants(
    stmt: Select,
    nomination_ids: list[NominationId] | None = None,
    search_query: str | None = None,
) -> Select:
    filters = []
    if nomination_ids:
        filters.append(
            ParticipantORM.nomination.has(NominationORM.id.in_(nomination_ids))
        )
    if search_query:
        filters.append(
            or_(
                ParticipantORM.title.ilike(f"%{search_query}%"),
                ParticipantORM.voting_number == int(search_query)
                if search_query.isnumeric()
                else False,
            )
        )
    return stmt.where(*filters)


class SqlParticipantGateway(ParticipantRepository, ParticipantQuery):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ParticipantMapper()

    async def add(self, participant: Participant) -> None:
        participant_orm = self.mapper.from_model(participant)
        self.session.add(participant_orm)
        await self.session.flush([participant_orm])
        return

    async def get_by_cosplay2_id(self, cosplay2_id: int) -> Participant | None:
        stmt = (
            select(ParticipantORM)
            .where(ParticipantORM.cosplay2_id == cosplay2_id)
            .options(joinedload(ParticipantORM.values))
            .with_for_update(of=ParticipantORM)
        )
        participant_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(participant_orm) if participant_orm else None

    async def save(self, participant: Participant) -> None:
        participant_orm = await self.session.merge(self.mapper.from_model(participant))
        await self.session.flush([participant_orm])
        return

    async def read_list_participants(
        self,
        user_id: UserId,
        nomination_id: NominationId | None = None,
        search_query: str | None = None,
        pagination: Pagination | None = None,
    ) -> list[ParticipantFullDTO]:
        stmt = _select_participant_dto(user_id)

        stmt = _filter_participants(
            stmt=stmt, nomination_ids=[nomination_id], search_query=search_query
        )

        user_unique_order = func.md5(
            func.concat(str(user_id), "-", cast(ParticipantORM.id, String))
        )
        stmt = stmt.order_by(user_unique_order)

        if pagination:
            stmt = stmt.limit(pagination.limit).offset(pagination.offset)

        result = (await self.session.execute(stmt)).all()

        return [
            self.mapper.parse_full_dto(
                participant_orm=participant_orm, vote_orm=vote_orm
            )
            for participant_orm, vote_orm in result
        ]

    async def list_cosplay2_ids(self) -> list[int]:
        stmt = select(ParticipantORM.cosplay2_id)
        return list((await self.session.scalars(stmt)).all())

    async def delete_by_cosplay2_ids(self, cosplay2_ids: list[int]) -> None:
        if not cosplay2_ids:
            return
        await self.session.execute(
            delete(ParticipantORM).where(ParticipantORM.cosplay2_id.in_(cosplay2_ids))
        )

    async def delete(self, participant: Participant) -> None:
        await self.session.execute(
            delete(ParticipantORM).where(ParticipantORM.id == participant.id)
        )
