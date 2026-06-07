from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.feedback import FeedbackId
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class Feedback(AggregateRoot):
    id: FeedbackId
    user_id: UserId
    text: str
