from fanfan.adapters.db.models import UserORM
from fanfan.application.dto.user import (
    CurrentUserDTO,
    UserBaseDTO,
    UserDetailsDTO,
    UserListItemDTO,
    UserSettingsDTO,
    UserSocialIdentityDTO,
    UserSocialLinkDTO,
    UserTicketDTO,
)
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.email import Email
from fanfan.core.vo.permission import Permission
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
            receive_vk_notifications=model.settings.receive_vk_notifications,
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
                receive_vk_notifications=orm.receive_vk_notifications,
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
    def parse_list_item_dto(orm: UserORM) -> UserListItemDTO:
        return UserListItemDTO(
            id=UserId(orm.id),
            username=orm.username,
            role=orm.role,
            email=orm.email,
        )

    @staticmethod
    def parse_details_dto(orm: UserORM) -> UserDetailsDTO:
        return UserDetailsDTO(
            id=UserId(orm.id),
            username=orm.username,
            role=orm.role,
            email=orm.email,
            social_links=[
                UserSocialLinkDTO(
                    provider=identity.provider,
                    # provider_user_id is BIGINT; stringify so a >2^53 Telegram
                    # id survives the JSON round-trip without precision loss.
                    id=str(identity.provider_user_id),
                )
                for identity in orm.social_identities
            ],
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
            permissions=[Permission(p.permission) for p in orm.permissions],
            settings=UserSettingsDTO(
                receive_all_announcements=orm.receive_all_announcements,
                receive_telegram_notifications=orm.receive_telegram_notifications,
                receive_vk_notifications=orm.receive_vk_notifications,
            ),
            social_identities=[
                UserSocialIdentityDTO(provider=social_identity.provider)
                for social_identity in orm.social_identities
            ],
        )
