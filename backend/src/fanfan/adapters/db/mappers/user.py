from fanfan.adapters.db.models import UserORM
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserPermissionDTO,
    UserSettingsDTO,
    UserSocialIdentityDTO,
    UserTicketDTO,
)
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.email import Email
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId, Username, UserRole


class UserMapper:
    def from_model(self, model: User):
        return UserORM(
            id=model.id,
            username=model.username,
            hashed_password=model.hashed_password,
            email=model.email.value if model.email else None,
            role=model.role,
            # Queryable notification flags go to columns; the JSON bag is an
            # extension point for future non-queryable prefs (currently empty).
            receive_all_announcements=model.settings.receive_all_announcements,
            receive_telegram_notifications=model.settings.receive_telegram_notifications,
            settings={},
        )

    def to_model(self, orm: UserORM) -> User:
        return User(
            id=UserId(orm.id),
            username=Username(orm.username),
            hashed_password=orm.hashed_password,
            email=Email(orm.email) if orm.email else None,
            role=UserRole(orm.role),
            settings=UserSettings(
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
            permissions=[UserPermissionDTO(name=p.permission) for p in orm.permissions],
            settings=UserSettingsDTO(
                receive_all_announcements=orm.receive_all_announcements,
                receive_telegram_notifications=orm.receive_telegram_notifications,
            ),
            social_identities=[
                UserSocialIdentityDTO(
                    provider=social_identity.provider,
                    provider_id=social_identity.provider_id,
                )
                for social_identity in orm.social_identities
            ],
        )
