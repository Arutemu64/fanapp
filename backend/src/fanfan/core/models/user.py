from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fanfan.core.vo.user import UserId, Username, UserRole


@dataclass(slots=True, kw_only=True)
class UserSettings:
    items_per_page: int = 4
    receive_all_announcements: bool = True


@dataclass(slots=True, kw_only=True)
class User:  # noqa: PLW1641
    id: UserId | None = None

    username: Username | None
    hashed_password: str | None
    role: UserRole

    email: str | None = None
    is_verified: bool

    first_name: str | None = None
    last_name: str | None = None

    settings: UserSettings = field(default_factory=UserSettings)

    def set_username(self, username: Username | None):
        self.username = username

    def set_role(self, role: UserRole):
        self.role = role

    def __eq__(self, other: User | Any) -> bool:
        return isinstance(other, User) and self.id == other.id
