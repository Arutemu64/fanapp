from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from fanfan.adapters.db.mappers.feedback import FeedbackMapper
from fanfan.adapters.db.models import FeedbackORM
from fanfan.application.dto.feedback import FeedbackDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.core.models.feedback import Feedback


class SqlFeedbackGateway(FeedbackGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = FeedbackMapper()

    async def add(self, feedback: Feedback) -> None:
        feedback_orm = self.mapper.from_model(feedback)
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
        return [self.mapper.parse_dto(f) for f in feedback]
