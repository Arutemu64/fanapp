from datetime import datetime

from pydantic import BaseModel, Field

from fanfan.application.dto.input import InputModel
from fanfan.application.dto.user import UserRefDTO
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserRole


class TicketListFilter(BaseModel):
    search: str | None = None


class TicketListItemDTO(BaseModel):
    id: TicketId
    barcode: str
    role: UserRole
    used_by: UserRefDTO | None
    from_ticketscloud: bool
    revoked_at: datetime | None
    created_at: datetime


class TCloudEventRoleDTO(InputModel):
    event_id: str = Field(max_length=100)
    role: UserRole
