from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import UserId


class QuestPlayerDTO(BaseModel):
    id: UserId
    username: str
    avatar_seed: str
    points: int


class LeaderboardEntryDTO(BaseModel):
    rank: int
    player: QuestPlayerDTO


class QuestAwardUserDTO(BaseModel):
    id: UserId
    username: str


class QuestAwardDTO(BaseModel):
    id: QuestAwardId
    amount: int
    message: str
    created_at: datetime
    cancelled_at: datetime | None
    user: QuestAwardUserDTO
    awarded_by: QuestAwardUserDTO | None


class QuestAwardItemDTO(QuestAwardDTO):
    # Whether the viewer may cancel this award right now, so the list offers
    # the button only when the server would accept it.
    can_cancel: bool
