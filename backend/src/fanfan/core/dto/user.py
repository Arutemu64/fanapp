from pydantic import BaseModel, ConfigDict, EmailStr

from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, UserRole


class UserBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str | None
    first_name: str | None
    role: UserRole


class UserPermissionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: PermissionName
    object_type: PermissionObjectType | None
    object_id: PermissionObjectId | None


class UserTicketDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: TicketId
    barcode: str
    role: UserRole


class UserSettingsDTO(BaseModel):
    receive_all_announcements: bool = True
    receive_telegram_notifications: bool = True


class UserSocialAccountDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    provider_id: str


class UserFullDTO(UserBaseDTO):
    model_config = ConfigDict(from_attributes=True)

    ticket: UserTicketDTO | None
    permissions: list[UserPermissionDTO]
    settings: UserSettingsDTO  # TODO split into CurrentUser

    # TODO Remove this shortcut
    def check_permission(self, perm_name: PermissionName) -> bool:
        return any(p.name == perm_name for p in self.permissions)


class CurrentUserDTO(UserBaseDTO):
    email: EmailStr | None
    is_verified: bool
    has_password: bool

    ticket: UserTicketDTO | None
    permissions: list[UserPermissionDTO]
    settings: UserSettingsDTO
