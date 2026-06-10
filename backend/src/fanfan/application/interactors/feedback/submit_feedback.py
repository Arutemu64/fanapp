import logging

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.feedback import Feedback
from fanfan.core.vo.feedback import FeedbackId, generate_feedback_id

logger = logging.getLogger(__name__)


class SubmitFeedbackInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class SubmitFeedbackOutput(BaseModel):
    feedback_id: FeedbackId


class SubmitFeedback:
    def __init__(
        self,
        feedback_gateway: FeedbackGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.feedback_gateway = feedback_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(
        self,
        data: SubmitFeedbackInput,
    ) -> SubmitFeedbackOutput:
        current_user = await self.current_user_provider.require_user()
        feedback = Feedback(
            id=generate_feedback_id(),
            user_id=current_user.id,
            text=data.text,
        )
        await self.feedback_gateway.add(feedback)
        await self.uow.commit()
        logger.info(
            "Feedback %s submitted",
            feedback.id,
            extra={"user_feedback": feedback},
        )
        return SubmitFeedbackOutput(feedback_id=feedback.id)
