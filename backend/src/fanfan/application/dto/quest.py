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
    # A player's own view of an award: who gave it stays with the staff.
    id: QuestAwardId
    amount: int
    message: str
    created_at: datetime
    cancelled_at: datetime | None


class QuestAwardItemDTO(QuestAwardDTO):
    # Whether the viewer may cancel this award right now, so the list offers
    # the button only when the server would accept it.
    can_cancel: bool
