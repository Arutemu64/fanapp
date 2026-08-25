from pydantic import BaseModel, EmailStr

from fanfan.core.vo.permission import (
    Permission,
)
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class UserBaseDTO(BaseModel):
    id: UserId
    username: str
    role: UserRole


class UserListItemDTO(BaseModel):
    # A row in the organiser user directory (users:read). Email is carried so it
    # shows in the table and is matched by the server-side search.
    id: UserId
    username: str
    role: UserRole
    email: EmailStr | None


class UserSocialLinkDTO(BaseModel):
    # The provider's native account id (Telegram chat_id / VK id), exposed only
    # on the organiser user viewer (users:read) so staff can jump to the linked
    # account. The self-profile UserSocialIdentityDTO deliberately withholds it —
    # this is a different, permission-gated trust surface. Serialised as a string:
    # Telegram ids are BIGINT and can exceed JS's safe integer range, so a JSON
    # number would risk precision loss client-side.
    provider: SocialProvider
    id: str


class UserDetailsDTO(BaseModel):
    # Full organiser view of one user (users:read): the profile basics plus the
    # linked external accounts with their ids.
    id: UserId
    username: str
    role: UserRole
    email: EmailStr | None
    social_links: list[UserSocialLinkDTO]


class UserTicketDTO(BaseModel):
    id: TicketId
    barcode: str
    role: UserRole


class UserSettingsDTO(BaseModel):
    receive_all_announcements: bool = True
    receive_telegram_notifications: bool = True
    receive_vk_notifications: bool = True


class UserSocialIdentityDTO(BaseModel):
    # Which providers are linked is all the profile screen needs. The subject and
    # the provider's native user id stay server-side — shipping them would leak
    # an external account id to the client for nothing.
    provider: SocialProvider


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
