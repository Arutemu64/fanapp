from pydantic import BaseModel, EmailStr

from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class UserBaseDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole


class UserTicketDTO(BaseModel):
    id: TicketId
    barcode: str
    role: UserRole


class UserSettingsDTO(BaseModel):
    receive_all_announcements: bool = True
    receive_telegram_notifications: bool = True


class UserSocialIdentityDTO(BaseModel):
    provider: str
    provider_id: str


class CurrentUserDTO(UserBaseDTO):
    email: EmailStr | None
    has_password: bool

    ticket: UserTicketDTO | None
    # Bare list of granted permissions (a StrEnum, so it surfaces as a
    # Permission enum schema in OpenAPI): the frontend derives its literals from
    # that generated union with a compile-time drift guard.
    permissions: list[Permission]
    settings: UserSettingsDTO
    social_identities: list[UserSocialIdentityDTO]
