from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.mappers.feedback import FeedbackMapper
from fanfan.application.ports.repositories.feedback import FeedbackRepository
from fanfan.core.models.feedback import Feedback


class SqlFeedbackGateway(FeedbackRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = FeedbackMapper()

    async def add(self, feedback: Feedback) -> None:
        feedback_orm = self.mapper.from_model(feedback)
        self.session.add(feedback_orm)
        await self.session.flush([feedback_orm])
