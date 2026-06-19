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
    WILDCARD_PERMISSION,
    PermissionName,
    PermissionObjectId,
    PermissionObjectType,
)
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, Username, UserRole


class UserMapper:
    def __init__(self, retort: Retort):
        self.retort = retort

    def from_model(self, model: User):
        return UserORM(
            id=model.id,
            username=model.username,
            hashed_password=model.hashed_password,
            email=model.email.value if model.email else None,
            role=model.role,
            # Queryable notification flags go to columns; the rest stays in JSON.
            receive_all_announcements=model.settings.receive_all_announcements,
            receive_telegram_notifications=model.settings.receive_telegram_notifications,
            settings={"items_per_page": model.settings.items_per_page},
        )

    def to_model(self, orm: UserORM) -> User:
        return User(
            id=UserId(orm.id),
            username=Username(orm.username),
            hashed_password=orm.hashed_password,
            email=Email(orm.email) if orm.email else None,
            role=UserRole(orm.role),
            settings=UserSettings(
                items_per_page=orm.settings.get("items_per_page", 4),
                receive_all_announcements=orm.receive_all_announcements,
                receive_telegram_notifications=orm.receive_telegram_notifications,
            ),
        )

    @staticmethod
    def parse_base_dto(orm: UserORM) -> UserBaseDTO:
        return UserBaseDTO(
            id=UserId(orm.id),
            username=orm.username,
            role=orm.role,
        )

    @staticmethod
    def _resolve_permissions(orm: UserORM) -> list[UserPermissionDTO]:
        # ORG implicitly holds every permission (see PermissionService.ensure),
        # so it carries no explicit grant rows. Ship a single wildcard entry
        # instead of the empty list so the frontend resolves it as full access.
        if orm.role is UserRole.ORG:
            return [
                UserPermissionDTO(
                    name=WILDCARD_PERMISSION,
                    object_type=None,
                    object_id=None,
                )
            ]
        return [
            UserPermissionDTO(
                name=PermissionName(p.permission),
                object_type=PermissionObjectType(p.object_type)
                if p.object_type is not None
                else None,
                object_id=PermissionObjectId(p.object_id)
                if p.object_id is not None
                else None,
            )
            for p in orm.permissions
        ]

    def parse_current_user_dto(self, orm: UserORM) -> CurrentUserDTO:
        return CurrentUserDTO(
            id=UserId(orm.id),
            username=orm.username,
            role=orm.role,
            email=orm.email,
            has_password=bool(orm.hashed_password),
            ticket=UserTicketDTO(
                id=TicketId(orm.ticket.id),
                barcode=orm.ticket.barcode,
                role=orm.ticket.role,
            )
            if orm.ticket
            else None,
            permissions=self._resolve_permissions(orm),
            settings=UserSettingsDTO(
                receive_all_announcements=orm.receive_all_announcements,
                receive_telegram_notifications=orm.receive_telegram_notifications,
            ),
        )
