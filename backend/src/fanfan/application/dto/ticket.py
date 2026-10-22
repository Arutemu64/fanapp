from datetime import datetime

from pydantic import BaseModel, Field

from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class TicketListFilter(BaseModel):
    # `search` is a case-insensitive substring of the ticket number.
    search: str | None = None


class TicketListItemDTO(BaseModel):
    # A row in the organizer ticket list. created_at is the sort key the page
    # cursor points into.
    id: TicketId
    barcode: str
    role: UserRole
    used_by_user_id: UserId | None
    used_by_username: str | None
    # Imported tickets carry the vendor's ids; generated ones carry neither.
    from_ticketscloud: bool
    revoked_at: datetime | None
    created_at: datetime


class TCloudEventRoleDTO(BaseModel):
    event_id: str = Field(max_length=100)
    role: UserRole
