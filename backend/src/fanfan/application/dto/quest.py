from datetime import datetime

from pydantic import BaseModel

from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId, UserNumber


class QuestPlayerDTO(BaseModel):
    id: UserId
    number: UserNumber
    username: str
    avatar_seed: str
    points: int


class LeaderboardEntryDTO(BaseModel):
    rank: int
    player: QuestPlayerDTO


class QuestAwardDTO(BaseModel):
    id: QuestAwardId
    amount: int
    message: str
    created_at: datetime
    cancelled_at: datetime | None
    user: UserRefDTO
    awarded_by: UserRefDTO | None


class QuestHistoryItemDTO(BaseModel):
    id: QuestAwardId
    amount: int
    message: str
    created_at: datetime
    cancelled_at: datetime | None


class QuestAwardItemDTO(QuestAwardDTO):
    can_cancel: bool
