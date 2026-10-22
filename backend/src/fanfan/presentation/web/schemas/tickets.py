from typing import Annotated

from pydantic import BaseModel, Field


class TicketListQuery(BaseModel):
    """Query string of GET /tickets, read as one model
    (https://fastapi.tiangolo.com/tutorial/query-param-models/)."""

    limit: Annotated[int, Field(ge=1, le=100)] = 20
    cursor: Annotated[
        str | None,
        Field(
            max_length=200,
            description="Opaque `next_cursor` from the previous page; omit it for "
            "the first page.",
        ),
    ] = None
    search: Annotated[str | None, Field(max_length=100)] = None
