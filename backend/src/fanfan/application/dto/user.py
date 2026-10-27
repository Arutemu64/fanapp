from datetime import datetime

from pydantic import BaseModel, EmailStr

from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserNumber, UserRole


class UserRefDTO(BaseModel):
    """A person attached to a record, in the field named for their role there
    (`user`, `awarded_by`, `created_by`, …); null when nobody is (a system
    action, a deleted account)."""

    id: UserId
    username: str


class UserBaseDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole


class UserListFilter(BaseModel):
    search: str | None = None
    role: UserRole | None = None
    has_ticket: bool | None = None


class UserListItemDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole
    email: EmailStr | None
    avatar_seed: str
    ticket_number: str | None
    created_at: datetime


class UserSocialLinkDTO(BaseModel):
    provider: SocialProvider
    id: str


class UserDetailsDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole
    email: EmailStr | None
    avatar_seed: str
    ticket_number: str | None
    created_at: datetime
    social_links: list[UserSocialLinkDTO]
    permissions: list[Permission]


class UserTicketDTO(BaseModel):
    id: TicketId
    barcode: str
    role: UserRole


class UserSettingsDTO(BaseModel):
    receive_all_announcements: bool
    receive_telegram_notifications: bool
    receive_vk_notifications: bool


class UserSocialIdentityDTO(BaseModel):
    provider: SocialProvider


class CurrentUserDTO(UserBaseDTO):
    number: UserNumber
    email: EmailStr | None
    avatar_seed: str
    has_password: bool

    ticket: UserTicketDTO | None
    permissions: list[Permission]
    settings: UserSettingsDTO
    social_identities: list[UserSocialIdentityDTO]


class UsernameSuggestionDTO(BaseModel):
    username: str
