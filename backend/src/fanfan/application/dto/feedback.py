from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.feedback import FeedbackId
from fanfan.core.vo.user import UserId


class FeedbackUserDTO(BaseModel):
    id: UserId
    username: str


class FeedbackDTO(BaseModel):
    id: FeedbackId
    text: str
    created_at: datetime
    # Always present: user_id is NOT NULL with ON DELETE CASCADE, so a deleted
    # author takes the feedback row with it rather than orphaning it.
    user: FeedbackUserDTO
