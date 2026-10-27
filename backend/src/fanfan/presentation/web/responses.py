from typing import Any

from starlette import status

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
    """OpenAPI doc for a `Location` header; its value is a path from the API root."""
    return {"Location": {"schema": {"type": "string"}, "description": description}}


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
