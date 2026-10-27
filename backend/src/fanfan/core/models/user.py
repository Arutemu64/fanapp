from dataclasses import dataclass, field
from typing import Self, override

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import (
    UserId,
    Username,
    UserNumber,
    UserRole,
    generate_avatar_seed,
    generate_user_number,
)


@dataclass(slots=True, kw_only=True)
class UserSettings:
    receive_all_announcements: bool = False
    receive_telegram_notifications: bool = True
    receive_vk_notifications: bool = True


@dataclass(slots=True, kw_only=True)
class User(AggregateRoot):
    id: UserId

    username: Username
    hashed_password: str | None
    role: UserRole

    email: Email | None = None
    avatar_seed: str = field(default_factory=generate_avatar_seed)
    number: UserNumber = field(default_factory=generate_user_number)

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

    def redraw_number(self) -> None:
        self.number = generate_user_number()

    def set_avatar_seed(self, avatar_seed: str) -> None:
        self.avatar_seed = avatar_seed

    def update_settings(
        self,
        *,
        receive_all_announcements: bool | None = None,
        receive_telegram_notifications: bool | None = None,
        receive_vk_notifications: bool | None = None,
    ) -> None:
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

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, User) and self.id == other.id

    @override
    def __hash__(self) -> int:
        return hash(self.id)
