from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.models import FeedbackORM
from fanfan.adapters.db.pagination import rows_after
from fanfan.adapters.db.user_ref import parse_user_ref
from fanfan.application.dto.feedback import FeedbackDTO
from fanfan.application.dto.page import CursorPagination
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.core.models.feedback import Feedback
from fanfan.core.vo.feedback import FeedbackId


def _from_model(model: Feedback) -> FeedbackORM:
    return FeedbackORM(
        id=model.id,
        user_id=model.user_id,
        text=model.text,
    )


def _parse_dto(orm: FeedbackORM) -> FeedbackDTO:
    return FeedbackDTO(
        id=FeedbackId(orm.id),
        text=orm.text,
        created_at=orm.created_at,
        user=parse_user_ref(orm.user),
    )


class SqlFeedbackGateway(FeedbackGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, feedback: Feedback) -> None:
        feedback_orm = _from_model(feedback)
        self.session.add(feedback_orm)
        await self.session.flush()

    async def read_list_feedback(
        self, pagination: CursorPagination
    ) -> list[FeedbackDTO]:
        # id (uuid7, time-ordered) is the tiebreaker so rows sharing a created_at
        # — feedback submitted within the same clock tick — keep a stable,
        # newest-first order the page cursor can point into.
        stmt = (
            select(FeedbackORM)
            .order_by(FeedbackORM.created_at.desc(), FeedbackORM.id.desc())
            .options(joinedload(FeedbackORM.user))
            .limit(pagination.fetch_limit)
        )
        if pagination.after is not None:
            stmt = stmt.where(
                rows_after(FeedbackORM.created_at, FeedbackORM.id, pagination.after)
            )
        feedback = await self.session.scalars(stmt)
        return [_parse_dto(f) for f in feedback]
