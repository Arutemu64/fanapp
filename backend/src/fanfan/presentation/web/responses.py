from typing import Any

from starlette import status
from starlette.requests import Request

from fanfan.presentation.web.schemas.error import ProblemDetails, ValidationProblem

VALIDATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ValidationProblem,
        "description": "Request validation error.",
    },
}

AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ProblemDetails,
        "description": "Not authenticated.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ProblemDetails,
        "description": "Access denied.",
    },
}


def location_header(description: str) -> dict[str, Any]:
    """OpenAPI doc for a `Location` header; its value is an absolute path."""
    return {"Location": {"schema": {"type": "string"}, "description": description}}


def resource_location(request: Request, path: str) -> str:
    """A `Location` value for a route path, under the `/api` prefix the proxy strips."""
    return f"{request.scope.get('root_path', '')}{path}"


RATE_LIMIT_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ProblemDetails,
        "description": "Rate limited — too many requests.",
        "headers": {
            "Retry-After": {
                "schema": {"type": "integer"},
                "description": "Seconds to wait before retrying.",
            }
        },
    },
}
