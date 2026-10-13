from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import InstrumentedAttribute

from fanfan.application.dto.page import PageCursor


def rows_after(
    created_at: InstrumentedAttribute[datetime],
    row_id: InstrumentedAttribute[UUID],
    cursor: PageCursor,
) -> ColumnElement[bool]:
    """Rows past ``cursor`` in a (created_at DESC, id DESC) sort.

    Spelled out instead of the row-value ``(created_at, id) < (:t, :id)``: the
    redundant ``created_at <= :t`` is a plain range an index on created_at alone
    can seek, which the row comparison is not when id is missing from the index
    (https://use-the-index-luke.com/sql/partial-results/fetch-next-page).
    """
    return and_(
        created_at <= cursor.created_at,
        or_(
            created_at < cursor.created_at,
            row_id < cursor.id,
        ),
    )
