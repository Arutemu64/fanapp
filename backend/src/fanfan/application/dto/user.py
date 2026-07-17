from pydantic import BaseModel, EmailStr

from fanfan.core.vo.permission import (
    Permissions,
)
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class UserBaseDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole


class UserPermissionDTO(BaseModel):
    # Typed as the Permissions enum (not the plain PermissionName str) so the
    # OpenAPI spec exposes a Permissions enum schema, giving the frontend a
    # generated, drift-guarded union instead of hand-copied literals.
    name: Permissions


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
    permissions: list[UserPermissionDTO]
    settings: UserSettingsDTO
    social_identities: list[UserSocialIdentityDTO]
