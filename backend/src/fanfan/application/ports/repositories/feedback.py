from typing import Protocol

from fanfan.core.models.feedback import Feedback


class FeedbackRepository(Protocol):
    async def add(self, feedback: Feedback) -> None: ...
