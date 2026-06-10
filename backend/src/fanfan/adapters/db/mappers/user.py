from adaptix import Retort

from fanfan.adapters.db.models import UserORM
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserPermissionDTO,
    UserSettingsDTO,
    UserTicketDTO,
)
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.email import Email
from fanfan.core.vo.permission import (
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, Username, UserRole


class UserMapper:
    def __init__(self):
        self.retort = Retort()

    def from_model(self, model: User):
        return UserORM(
            id=model.id,
            username=model.username,
            hashed_password=model.hashed_password,
            email=model.email.value if model.email else None,
            pending_email=model.pending_email.value if model.pending_email else None,
            email_verified_at=model.email_verified_at,
            first_name=model.first_name,
            role=model.role,
            settings=self.retort.dump(model.settings),
        )

    def to_model(self, orm: UserORM) -> User:
        return User(
            id=UserId(orm.id),
            username=Username(orm.username) if orm.username is not None else None,
            hashed_password=orm.hashed_password,
            email=Email(orm.email) if orm.email else None,
            pending_email=Email(orm.pending_email) if orm.pending_email else None,
            email_verified_at=orm.email_verified_at,
            first_name=orm.first_name,
            role=UserRole(orm.role),
            settings=self.retort.load(orm.settings, UserSettings),
        )

    @staticmethod
    def parse_base_dto(orm: UserORM) -> UserBaseDTO:
        return UserBaseDTO(
            id=UserId(orm.id),
            username=orm.username,
            first_name=orm.first_name,
            role=orm.role,
        )

    def parse_current_user_dto(self, orm: UserORM) -> CurrentUserDTO:
        return CurrentUserDTO(
            id=UserId(orm.id),
            username=orm.username,
            first_name=orm.first_name,
            role=orm.role,
            email=orm.email,
            pending_email=orm.pending_email,
            email_verified_at=orm.email_verified_at,
            has_password=bool(orm.hashed_password),
            ticket=UserTicketDTO(
                id=TicketId(orm.ticket.id),
                barcode=orm.ticket.barcode,
                role=orm.ticket.role,
            )
            if orm.ticket
            else None,
            permissions=[
                UserPermissionDTO(
                    name=PermissionName(p.permission.name),
                    object_type=PermissionObjectType(p.object_type)
                    if p.object_type is not None
                    else None,
                    object_id=PermissionObjectId(p.object_id)
                    if p.object_id is not None
                    else None,
                )
                for p in orm.permissions
            ],
            settings=self.retort.load(orm.settings, UserSettingsDTO),
        )
