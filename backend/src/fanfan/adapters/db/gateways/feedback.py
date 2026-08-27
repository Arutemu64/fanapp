from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.models import FeedbackORM
from fanfan.application.dto.feedback import FeedbackDTO, FeedbackUserDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.core.models.feedback import Feedback
from fanfan.core.vo.feedback import FeedbackId
from fanfan.core.vo.user import UserId


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
        user=FeedbackUserDTO(
            id=UserId(orm.user.id),
            username=orm.user.username,
        ),
    )


class SqlFeedbackGateway(FeedbackGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, feedback: Feedback) -> None:
        feedback_orm = _from_model(feedback)
        self.session.add(feedback_orm)
        await self.session.flush([feedback_orm])

    async def read_list_feedback(self, pagination: Pagination) -> list[FeedbackDTO]:
        # id (uuid7, time-ordered) is the tiebreaker so rows sharing a created_at
        # — feedback submitted within the same clock tick — keep a stable,
        # newest-first order across paginated requests instead of shuffling.
        stmt = (
            select(FeedbackORM)
            .order_by(FeedbackORM.created_at.desc(), FeedbackORM.id.desc())
            .options(joinedload(FeedbackORM.user))
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        feedback = await self.session.scalars(stmt)
        return [_parse_dto(f) for f in feedback]
