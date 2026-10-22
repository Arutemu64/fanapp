from datetime import datetime

from pydantic import BaseModel, EmailStr

from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserNumber, UserRole


class UserBaseDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole


class UserListFilter(BaseModel):
    # Narrows the organizer user directory. Every field is optional and they
    # combine with AND; `search` is a case-insensitive substring of the username,
    # email or linked ticket number.
    search: str | None = None
    role: UserRole | None = None
    has_ticket: bool | None = None


class UserListItemDTO(BaseModel):
    # A row in the organizer user directory (users:read). Email is carried so it
    # shows in the list and is matched by the server-side search; created_at is
    # the sort key the page cursor points into.
    id: UserId
    username: str
    role: UserRole
    email: EmailStr | None
    avatar_seed: str
    ticket_number: str | None
    created_at: datetime


class UserSocialLinkDTO(BaseModel):
    # The provider's native account id (Telegram chat_id / VK id), exposed only
    # on the organizer user viewer (users:read) so staff can jump to the linked
    # account. The self-profile UserSocialIdentityDTO deliberately withholds it —
    # this is a different, permission-gated trust surface. Serialised as a string:
    # Telegram ids are BIGINT and can exceed JS's safe integer range, so a JSON
    # number would risk precision loss client-side.
    provider: SocialProvider
    id: str


class UserDetailsDTO(BaseModel):
    # Full organizer view of one user (users:read): the profile basics, the
    # linked external accounts with their ids, and the granted permissions.
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
    receive_all_announcements: bool = False
    receive_telegram_notifications: bool = True
    receive_vk_notifications: bool = True


class UserSocialIdentityDTO(BaseModel):
    # Which providers are linked is all the profile screen needs. The subject and
    # the provider's native user id stay server-side — shipping them would leak
    # an external account id to the client for nothing.
    provider: SocialProvider


class CurrentUserDTO(UserBaseDTO):
    number: UserNumber
    email: EmailStr | None
    avatar_seed: str
    has_password: bool

    ticket: UserTicketDTO | None
    # Bare list of granted permissions (a StrEnum, so it surfaces as a
    # Permission enum schema in OpenAPI): the frontend derives its literals from
    # that generated union with a compile-time drift guard.
    permissions: list[Permission]
    settings: UserSettingsDTO
    social_identities: list[UserSocialIdentityDTO]


class UsernameSuggestionDTO(BaseModel):
    username: str
