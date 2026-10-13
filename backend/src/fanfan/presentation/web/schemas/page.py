from typing import Annotated

from fastapi import Query

PageCursorQuery = Annotated[
    str | None,
    Query(
        max_length=200,
        description="Opaque `next_cursor` from the previous page; omit it for the "
        "first page.",
    ),
]
