from sqlalchemy import Select, and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.mappers.participant import ParticipantMapper
from fanfan.adapters.db.models import (
    NominationORM,
    ParticipantORM,
    VoteORM,
)
from fanfan.application.dto.participant import ParticipantFullDTO
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId
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


class SqlParticipantGateway(ParticipantGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = ParticipantMapper()

    async def add(self, participant: Participant) -> None:
        participant_orm = self.mapper.from_model(participant)
        self.session.add(participant_orm)
        await self.session.flush([participant_orm])
        return

    async def get(self, participant_id: ParticipantId) -> Participant | None:
        stmt = (
            select(ParticipantORM)
            .where(ParticipantORM.id == participant_id)
            .options(joinedload(ParticipantORM.values))
            .with_for_update(of=ParticipantORM)
        )
        participant_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(participant_orm) if participant_orm else None

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
        user_id: UserId | None = None,
        nomination_id: NominationId | None = None,
    ) -> list[ParticipantFullDTO]:
        stmt = _select_participant_dto(user_id)

        stmt = stmt.where(
            ParticipantORM.nomination.has(NominationORM.id == nomination_id)
        ).order_by(ParticipantORM.voting_number)

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
