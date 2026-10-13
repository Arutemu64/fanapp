from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from fanfan.application.dto.page import CursorPagination, PageCursor, cut_page
from fanfan.core.exceptions.pagination import InvalidPageCursor

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _Row:
    id: UUID
    created_at: datetime


def test_cursor_round_trips_through_its_token() -> None:
    cursor = PageCursor(
        created_at=datetime(2026, 5, 1, 12, 30, 15, 123456, tzinfo=UTC), id=uuid4()
    )

    assert PageCursor.decode(cursor.encode()) == cursor


@pytest.mark.parametrize(
    "token",
    [
        "not base64 !",
        "bm90IGpzb24",  # "not json"
        "eyJ0IjogIjIwMjYtMDUtMDEifQ",  # {"t": "2026-05-01"}: no id
        # {"t": "2026-05-01T12:00:00", "id": <uuid>}: naive timestamp
        "eyJ0IjogIjIwMjYtMDUtMDFUMTI6MDA6MDAiLCAiaWQiOiAiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIn0",
    ],
)
def test_malformed_token_is_rejected(token: str) -> None:
    with pytest.raises(InvalidPageCursor):
        PageCursor.decode(token)


def test_cut_page_points_next_cursor_at_the_last_row_kept() -> None:
    now = datetime.now(UTC)
    rows = [_Row(id=uuid4(), created_at=now) for _ in range(3)]
    pagination = CursorPagination(limit=2)

    page, next_cursor = cut_page(rows, pagination)

    assert page == rows[:2]
    assert next_cursor is not None
    assert PageCursor.decode(next_cursor) == PageCursor(created_at=now, id=rows[1].id)


def test_cut_page_without_the_extra_row_is_the_last_page() -> None:
    rows = [_Row(id=uuid4(), created_at=datetime.now(UTC)) for _ in range(2)]

    page, next_cursor = cut_page(rows, CursorPagination(limit=2))

    assert page == rows
    assert next_cursor is None
