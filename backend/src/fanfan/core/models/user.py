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

    def set_username(self, username: Username | None):
        self.username = username

    def set_role(self, role: UserRole):
        self.role = role

    def __eq__(self, other: User | Any) -> bool:
        return isinstance(other, User) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
