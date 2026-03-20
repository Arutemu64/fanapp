from adaptix import Retort

from fanfan.adapters.db.models import UserORM
from fanfan.core.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserPermissionDTO,
    UserSettingsDTO,
    UserTicketDTO,
)
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.user import UserId, UserRole


class UserMapper:
    def __init__(self):
        self.retort = Retort()

    def from_model(self, model: User):
        return UserORM(
            id=model.id,
            username=model.username,
            hashed_password=model.hashed_password,
            email=model.email,
            pending_email=model.pending_email,
            email_verified_at=model.email_verified_at,
            first_name=model.first_name,
            role=model.role,
            settings=self.retort.dump(model.settings),
        )

    def to_model(self, orm: UserORM) -> User:
        return User(
            id=UserId(orm.id),
            username=orm.username,
            hashed_password=orm.hashed_password,
            email=orm.email,
            pending_email=orm.pending_email,
            email_verified_at=orm.email_verified_at,
            first_name=orm.first_name,
            role=UserRole(orm.role),
            settings=self.retort.load(orm.settings, UserSettings),
        )

    @staticmethod
    def parse_base_dto(orm: UserORM) -> UserBaseDTO:
        return UserBaseDTO(
            id=orm.id,
            username=orm.username,
            first_name=orm.first_name,
            role=orm.role,
        )

    def parse_current_user_dto(self, orm: UserORM) -> CurrentUserDTO:
        return CurrentUserDTO(
            id=orm.id,
            username=orm.username,
            first_name=orm.first_name,
            role=orm.role,
            email=orm.email,
            pending_email=orm.pending_email,
            email_verified_at=orm.email_verified_at,
            has_password=bool(orm.hashed_password),
            ticket=UserTicketDTO(
                id=orm.ticket.id, barcode=orm.ticket.barcode, role=orm.ticket.role
            )
            if orm.ticket
            else None,
            permissions=[
                UserPermissionDTO(
                    name=p.permission.name,
                    object_type=p.object_type,
                    object_id=p.object_id,
                )
                for p in orm.permissions
            ],
            settings=self.retort.load(orm.settings, UserSettingsDTO),
        )
