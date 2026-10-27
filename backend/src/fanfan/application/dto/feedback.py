from datetime import datetime

from pydantic import BaseModel

from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.feedback import FeedbackId


class FeedbackDTO(BaseModel):
    id: FeedbackId
    text: str
    created_at: datetime
    user: UserRefDTO
