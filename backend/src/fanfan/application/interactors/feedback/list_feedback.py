from pydantic import BaseModel

from fanfan.application.dto.feedback import FeedbackDTO
from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.feedback import FeedbackGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class ListFeedbackInput(BaseModel):
    pagination: Pagination


class ListFeedbackResult(BaseModel):
    feedback: list[FeedbackDTO]


class ListFeedback:
    def __init__(
        self,
        feedback_gateway: FeedbackGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.feedback_gateway = feedback_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: ListFeedbackInput) -> ListFeedbackResult:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.FEEDBACK_READ
        )
        feedback = await self.feedback_gateway.read_list_feedback(
            pagination=data.pagination
        )
        return ListFeedbackResult(feedback=feedback)
