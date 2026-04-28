from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid7

from fanfan.core.vo.user import UserId, Username, UserRole

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(slots=True, kw_only=True)
class UserSettings:
    items_per_page: int = 4
    receive_all_announcements: bool = True
    receive_telegram_notifications: bool = True

    def set_receive_all_announcements(self, value: bool) -> None:
        self.receive_all_announcements = value

    def set_receive_telegram_notifications(self, value: bool) -> None:
        self.receive_telegram_notifications = value


@dataclass(slots=True, kw_only=True)
class User:
    id: UserId = field(default_factory=uuid7)

    username: Username | None
    hashed_password: str | None
    role: UserRole

    email: str | None = None
    pending_email: str | None = None
    email_verified_at: datetime | None = None

    first_name: str | None = None

    settings: UserSettings = field(default_factory=UserSettings)

    def set_username(self, username: Username | None) -> None:
        self.username = username

    def set_role(self, role: UserRole) -> None:
        self.role = role

    def reset_ticket_role(self) -> None:
        self.role = UserRole.VISITOR

    def set_first_name(self, first_name: str | None) -> None:
        self.first_name = first_name

    def request_email_change(self, email: str) -> None:
        self.pending_email = email

    def confirm_pending_email(self, verified_at: datetime) -> None:
        self.email = self.pending_email
        self.pending_email = None
        self.email_verified_at = verified_at

    def verify_email(self, verified_at: datetime) -> None:
        self.email_verified_at = verified_at

    def set_password_hash(self, hashed_password: str) -> None:
        self.hashed_password = hashed_password

    def __eq__(self, other: User | Any) -> bool:
        return isinstance(other, User) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
