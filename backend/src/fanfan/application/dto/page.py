import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Self
from uuid import UUID

from fanfan.core.exceptions.pagination import InvalidPageCursor


@dataclass(kw_only=True, frozen=True, slots=True)
class PageCursor:
    """Position after the last row of a page sorted by (created_at, id) descending.

    It travels to the client as an opaque token so the encoding can change without
    breaking it (https://google.aip.dev/158). Both fields already appear in the
    page's rows, so the token reveals nothing; it grants nothing either — every
    read still applies its own filters and permission checks.
    """

    created_at: datetime
    id: UUID

    def encode(self) -> str:
        payload = json.dumps({"t": self.created_at.isoformat(), "id": str(self.id)})
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str) -> Self:
        padded = token + "=" * (-len(token) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded))
            raw_created_at, raw_id = payload["t"], payload["id"]
        except (binascii.Error, ValueError, TypeError, KeyError) as e:
            raise InvalidPageCursor from e
        if not isinstance(raw_created_at, str) or not isinstance(raw_id, str):
            raise InvalidPageCursor
        try:
            created_at = datetime.fromisoformat(raw_created_at)
            row_id = UUID(raw_id)
        except ValueError as e:
            raise InvalidPageCursor from e
        if created_at.tzinfo is None:
            raise InvalidPageCursor
        return cls(created_at=created_at, id=row_id)


@dataclass(kw_only=True, frozen=True, slots=True)
class CursorPagination:
    """Keyset paging: the next page starts after a cursor instead of an offset.

    Offset pages shift when rows are deleted ahead of them and skip unseen rows;
    a cursor pins the position to a row
    (https://use-the-index-luke.com/no-offset).
    """

    limit: int
    after: PageCursor | None = None

    @classmethod
    def from_token(cls, *, limit: int, cursor: str | None) -> Self:
        if cursor is None:
            return cls(limit=limit)
        return cls(limit=limit, after=PageCursor.decode(cursor))

    @property
    def fetch_limit(self) -> int:
        return self.limit + 1


class KeysetRow(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def created_at(self) -> datetime: ...


def cut_page[T: KeysetRow](
    rows: list[T], pagination: CursorPagination
) -> tuple[list[T], str | None]:
    """Split rows read with ``pagination.fetch_limit`` into the page and the
    ``next_cursor`` token, which is None on the last page."""
    page = rows[: pagination.limit]
    if len(rows) <= pagination.limit:
        return page, None
    last = page[-1]
    return page, PageCursor(created_at=last.created_at, id=last.id).encode()
