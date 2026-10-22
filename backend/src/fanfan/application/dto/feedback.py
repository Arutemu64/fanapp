from datetime import datetime

from pydantic import BaseModel

from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.feedback import FeedbackId


class FeedbackDTO(BaseModel):
    id: FeedbackId
    text: str
    created_at: datetime
    # Always present: user_id is NOT NULL with ON DELETE CASCADE, so a deleted
    # author takes the feedback row with it rather than orphaning it.
    user: UserRefDTO
