from typing import Protocol

from fanfan.core.models.feedback import Feedback


class FeedbackGateway(Protocol):
    async def add(self, feedback: Feedback) -> None: ...
