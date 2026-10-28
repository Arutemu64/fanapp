from typing import Annotated

from pydantic import Field

from fanfan.application.dto.input import InputModel
from fanfan.core.vo.user import UserRole


class UserListQuery(InputModel):
    """Query string of GET /users, read as one model
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
    q: Annotated[str | None, Field(max_length=100, description="Search term.")] = None
    role: UserRole | None = None
    has_ticket: bool | None = None


class SetUserRoleBody(InputModel):
    role: UserRole
