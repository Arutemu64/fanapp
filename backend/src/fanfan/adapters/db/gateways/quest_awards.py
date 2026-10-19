from typing import Any
from uuid import UUID

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import QuestAwardORM, UserORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.quest import (
    LeaderboardEntryDTO,
    QuestAwardDTO,
    QuestAwardUserDTO,
    QuestPlayerDTO,
)
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.quest import QuestAwardAlreadyExists
from fanfan.core.models.quest_award import QuestAward
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId


def _from_model(model: QuestAward) -> QuestAwardORM:
    return QuestAwardORM(
        id=model.id,
        user_id=model.user_id,
        amount=model.amount,
        message=model.message,
        awarded_by=model.awarded_by,
        created_at=model.created_at,
        cancelled_at=model.cancelled_at,
        cancelled_by=model.cancelled_by,
    )


def _to_model(orm: QuestAwardORM) -> QuestAward:
    awarded_by = None if orm.awarded_by is None else UserId(orm.awarded_by)
    cancelled_by = None if orm.cancelled_by is None else UserId(orm.cancelled_by)
    return QuestAward(
        id=QuestAwardId(orm.id),
        user_id=UserId(orm.user_id),
        amount=orm.amount,
        message=orm.message,
        awarded_by=awarded_by,
        created_at=orm.created_at,
        cancelled_at=orm.cancelled_at,
        cancelled_by=cancelled_by,
    )


def _parse_award_dto(orm: QuestAwardORM) -> QuestAwardDTO:
    awarded_by = None
    if orm.awarder is not None:
        awarded_by = QuestAwardUserDTO(
            id=UserId(orm.awarder.id), username=orm.awarder.username
        )
    return QuestAwardDTO(
        id=QuestAwardId(orm.id),
        amount=orm.amount,
        message=orm.message,
        created_at=orm.created_at,
        cancelled_at=orm.cancelled_at,
        user=QuestAwardUserDTO(id=UserId(orm.user.id), username=orm.user.username),
        awarded_by=awarded_by,
    )


def _parse_player_dto(row: Row[*tuple[Any, ...]]) -> QuestPlayerDTO:
    return QuestPlayerDTO(
        id=UserId(row.id),
        username=row.username,
        avatar_seed=row.avatar_seed,
        points=row.points,
    )


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlQuestAwardGateway(QuestAwardGateway):
    def __init__(self, session: AsyncSession, uow: UnitOfWork) -> None:
        self.session = session
        self.uow = uow

    async def add(self, award: QuestAward) -> None:
        # Two concurrent requests with one client ID can both pass the
        # interactor's lookup; the second one lands here (docs/adr/0034).
        with translate_integrity_error({"pk_quest_awards": QuestAwardAlreadyExists}):
            self.session.add(_from_model(award))
            await self.session.flush()
        self.uow.register(award)

    async def get(self, award_id: QuestAwardId) -> QuestAward | None:
        orm = await self.session.get(QuestAwardORM, award_id)
        if orm is None:
            return None
        return _to_model(orm)

    async def get_for_update(self, award_id: QuestAwardId) -> QuestAward | None:
        stmt = (
            select(QuestAwardORM).where(QuestAwardORM.id == award_id).with_for_update()
        )
        orm = await self.session.scalar(stmt)
        if orm is None:
            return None
        award = _to_model(orm)
        self.uow.register(award)
        return award

    async def save(self, award: QuestAward) -> None:
        await self.session.merge(_from_model(award))
        await self.session.flush()

    # Read projections (return DTOs, not aggregates)

    def _players_stmt(self) -> Select[UUID, str, str, Any]:
        live_points = (
            select(
                QuestAwardORM.user_id,
                func.sum(QuestAwardORM.amount).label("points"),
            )
            .where(QuestAwardORM.cancelled_at.is_(None))
            .group_by(QuestAwardORM.user_id)
            .subquery()
        )
        return select(
            UserORM.id,
            UserORM.username,
            UserORM.avatar_seed,
            func.coalesce(live_points.c.points, 0).label("points"),
        ).outerjoin(live_points, live_points.c.user_id == UserORM.id)

    async def read_player(self, user_id: UserId) -> QuestPlayerDTO | None:
        stmt = self._players_stmt().where(UserORM.id == user_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        return _parse_player_dto(row)

    async def read_players_by_username(
        self, search: str, limit: int
    ) -> list[QuestPlayerDTO]:
        # Prefix, case-insensitive: a volunteer types the start of the name the
        # player reads out. %/_ are escaped so they match literally.
        pattern = f"{_escape_like(search.strip().lower())}%"
        stmt = (
            self._players_stmt()
            .where(func.lower(UserORM.username).like(pattern))
            .order_by(func.lower(UserORM.username))
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        return [_parse_player_dto(row) for row in rows]

    async def read_leaderboard(
        self, *, limit: int, user_id: UserId
    ) -> tuple[list[LeaderboardEntryDTO], LeaderboardEntryDTO | None]:
        totals = (
            select(
                QuestAwardORM.user_id,
                func.sum(QuestAwardORM.amount).label("points"),
                func.max(QuestAwardORM.created_at).label("reached_at"),
            )
            .where(QuestAwardORM.cancelled_at.is_(None))
            .group_by(QuestAwardORM.user_id)
            .subquery()
        )
        # Merch goes to the top places, so ties must not share a rank: of two
        # players on the same score, whoever reached it first ranks higher.
        # The user id is only a last resort to keep the order stable.
        rank = (
            func.row_number()
            .over(
                order_by=(
                    totals.c.points.desc(),
                    totals.c.reached_at.asc(),
                    totals.c.user_id.asc(),
                )
            )
            .label("rank")
        )
        ranked = (
            select(totals.c.user_id, totals.c.points, rank)
            .where(totals.c.points > 0)
            .subquery()
        )
        stmt = (
            select(
                ranked.c.rank,
                ranked.c.points,
                UserORM.id,
                UserORM.username,
                UserORM.avatar_seed,
            )
            .join(UserORM, UserORM.id == ranked.c.user_id)
            .where(or_(ranked.c.rank <= limit, ranked.c.user_id == user_id))
            .order_by(ranked.c.rank)
        )
        rows = await self.session.execute(stmt)

        top: list[LeaderboardEntryDTO] = []
        own: LeaderboardEntryDTO | None = None
        for row in rows:
            entry = LeaderboardEntryDTO(rank=row.rank, player=_parse_player_dto(row))
            if row.rank <= limit:
                top.append(entry)
            if row.id == user_id:
                own = entry
        return top, own

    async def read_awards_page(
        self,
        *,
        pagination: CursorPagination,
        awarded_by: UserId | None = None,
        user_id: UserId | None = None,
    ) -> list[QuestAwardDTO]:
        stmt = (
            select(QuestAwardORM)
            .order_by(QuestAwardORM.created_at.desc(), QuestAwardORM.id.desc())
            .options(
                joinedload(QuestAwardORM.user),
                joinedload(QuestAwardORM.awarder),
            )
            .limit(pagination.fetch_limit)
        )
        if awarded_by is not None:
            stmt = stmt.where(QuestAwardORM.awarded_by == awarded_by)
        if user_id is not None:
            stmt = stmt.where(QuestAwardORM.user_id == user_id)
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(QuestAwardORM.created_at, QuestAwardORM.id, pagination.after)
            )
        awards = await self.session.scalars(stmt)
        return [_parse_award_dto(award) for award in awards]
