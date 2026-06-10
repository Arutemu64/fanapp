from dataclasses import dataclass

from fanfan.core.exceptions.users import InvalidEmail
from fanfan.core.utils.email import normalize_email


@dataclass(frozen=True, slots=True)
class Email:
    """A user's email address, stored normalized (trimmed + lowercased).

    Strict format validation lives at the API boundary (Pydantic's EmailStr).
    Here we only normalize and enforce a minimal sanity invariant, so the
    domain can never hold an obviously broken address. Compared by value.
    """

    value: str

    def __post_init__(self) -> None:
        normalized = normalize_email(self.value)
        local, _, domain = normalized.partition("@")
        if not local or not domain:
            raise InvalidEmail
        # Frozen dataclass: store the normalized form via object.__setattr__.
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
