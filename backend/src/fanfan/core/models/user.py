from dataclasses import dataclass, field
from typing import Any, Self

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import UserId, Username, UserRole


@dataclass(slots=True, kw_only=True)
class UserSettings:
    receive_all_announcements: bool = True
    receive_telegram_notifications: bool = True
    receive_vk_notifications: bool = True


@dataclass(slots=True, kw_only=True)
class User(AggregateRoot):
    id: UserId

    username: Username
    hashed_password: str | None
    role: UserRole

    email: Email | None = None

    settings: UserSettings = field(default_factory=UserSettings)

    @classmethod
    def create(
        cls,
        *,
        id: UserId,  # noqa: A002
        username: Username,
        hashed_password: str | None,
        role: UserRole,
        email: Email | None = None,
    ) -> Self:
        return cls(
            id=id,
            username=username,
            hashed_password=hashed_password,
            role=role,
            email=email,
        )

    def set_username(self, username: Username) -> None:
        self.username = username

    def set_role(self, role: UserRole) -> None:
        self.role = role

    def update_settings(
        self,
        *,
        receive_all_announcements: bool | None = None,
        receive_telegram_notifications: bool | None = None,
        receive_vk_notifications: bool | None = None,
    ) -> None:
        # Only the fields that were explicitly passed get changed; None means
        # "leave as is". Mutation goes through the aggregate root so callers
        # never reach into the settings object directly.
        if receive_all_announcements is not None:
            self.settings.receive_all_announcements = receive_all_announcements
        if receive_telegram_notifications is not None:
            self.settings.receive_telegram_notifications = (
                receive_telegram_notifications
            )
        if receive_vk_notifications is not None:
            self.settings.receive_vk_notifications = receive_vk_notifications

    def set_email(self, email: Email) -> None:
        self.email = email

    def set_password_hash(self, hashed_password: str) -> None:
        self.hashed_password = hashed_password

    def __eq__(self, other: User | Any) -> bool:
        return isinstance(other, User) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
