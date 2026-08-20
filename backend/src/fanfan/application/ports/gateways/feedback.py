from typing import Protocol

from fanfan.application.dto.feedback import FeedbackDTO
from fanfan.application.dto.page import Pagination
from fanfan.core.models.feedback import Feedback


class FeedbackGateway(Protocol):
    async def add(self, feedback: Feedback) -> None: ...

    async def read_list_feedback(self, pagination: Pagination) -> list[FeedbackDTO]: ...
