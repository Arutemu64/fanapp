from sqlalchemy import Select, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from fanfan.adapters.db.models import NominationORM, ParticipantORM, VoteORM
from fanfan.application.dto.nomination import NominationVoteDTO, NominationVotingDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.dto.voting import ContenderDTO, NominationContenderDTO
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import NominationCode, NominationId
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


def _from_model(model: Nomination) -> NominationORM:
    return NominationORM(
        id=model.id,
        cosplay2_id=model.cosplay2_id,
        code=model.code,
        title=model.title,
        is_votable=model.is_votable,
        works_url=model.works_url,
    )


def _to_model(orm: NominationORM) -> Nomination:
    return Nomination(
        id=NominationId(orm.id),
        cosplay2_id=orm.cosplay2_id,
        code=orm.code,
        title=orm.title,
        is_votable=orm.is_votable,
        works_url=orm.works_url,
    )


def _parse_voting_dto(
    nomination_orm: NominationORM, vote_orm: VoteORM | None
) -> NominationVotingDTO:
    return NominationVotingDTO(
        id=NominationId(nomination_orm.id),
        code=NominationCode(nomination_orm.code),
        title=nomination_orm.title,
        works_url=nomination_orm.works_url,
        participants_count=nomination_orm.participants_count,
        user_vote=NominationVoteDTO(
            id=VoteId(vote_orm.id),
            participant_id=ParticipantId(vote_orm.participant_id),
        )
        if vote_orm
        else None,
    )


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

    async def add(self, nomination: Nomination) -> None:
        nomination_orm = _from_model(nomination)
        self.session.add(nomination_orm)
        await self.session.flush([nomination_orm])

    async def get_by_cosplay2_id(self, cosplay2_id: int) -> Nomination | None:
        stmt = (
            select(NominationORM)
            .where(NominationORM.cosplay2_id == cosplay2_id)
            .with_for_update()
        )
        nomination_orm = await self.session.scalar(stmt)
        return _to_model(nomination_orm) if nomination_orm else None

    async def count_votable(self) -> int:
        stmt = select(func.count(NominationORM.id)).where(
            NominationORM.is_votable.is_(True)
        )
        return await self.session.scalar(stmt) or 0

    async def read_voting_contenders(self) -> list[NominationContenderDTO]:
        # Rank participants within each nomination by vote count, so the leader is
        # rank 1. voting_number breaks ties for a stable, deterministic pick.
        votes_count = func.count(VoteORM.id)
        ranked = (
            select(
                ParticipantORM.id.label("participant_id"),
                ParticipantORM.title.label("participant_title"),
                ParticipantORM.nomination_id.label("nomination_id"),
                votes_count.label("votes_count"),
                func.row_number()
                .over(
                    partition_by=ParticipantORM.nomination_id,
                    order_by=(votes_count.desc(), ParticipantORM.voting_number.asc()),
                )
                .label("rank"),
            )
            .outerjoin(VoteORM, VoteORM.participant_id == ParticipantORM.id)
            .group_by(ParticipantORM.id)
            .subquery()
        )

        # Total votes in the nomination — context for how commanding the lead is.
        total_votes = (
            select(func.count(VoteORM.id))
            .join(ParticipantORM, VoteORM.participant_id == ParticipantORM.id)
            .where(ParticipantORM.nomination_id == NominationORM.id)
            .correlate(NominationORM)
            .scalar_subquery()
        )

        stmt = (
            select(
                NominationORM.id,
                NominationORM.code,
                NominationORM.title,
                total_votes.label("total_votes"),
                ranked.c.participant_id,
                ranked.c.participant_title,
                ranked.c.votes_count,
            )
            .outerjoin(
                ranked,
                and_(
                    ranked.c.nomination_id == NominationORM.id,
                    ranked.c.rank == 1,
                ),
            )
            .where(NominationORM.is_votable.is_(True))
            .order_by(NominationORM.title)
        )

        rows = (await self.session.execute(stmt)).all()

        contenders: list[NominationContenderDTO] = []
        for row in rows:
            # A rank-1 participant on zero votes is not a real leader: keep
            # leader=None until at least one vote is cast (also covers a
            # nomination with no participants, where the outer join is NULL).
            if row.participant_id is not None and row.votes_count > 0:
                leader = ContenderDTO(
                    participant_id=ParticipantId(row.participant_id),
                    title=row.participant_title,
                    votes_count=row.votes_count,
                )
            else:
                leader = None
            contenders.append(
                NominationContenderDTO(
                    id=NominationId(row.id),
                    code=NominationCode(row.code),
                    title=row.title,
                    total_votes=row.total_votes,
                    leader=leader,
                )
            )
        return contenders

    async def save(self, nomination: Nomination) -> None:
        nomination_orm = await self.session.merge(_from_model(nomination))
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
            return _parse_voting_dto(nomination_orm=nomination_orm, vote_orm=vote_orm)
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
            _parse_voting_dto(nomination_orm=nomination_orm, vote_orm=vote_orm)
            for nomination_orm, vote_orm in results
        ]
