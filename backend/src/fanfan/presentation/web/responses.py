from typing import Any

from starlette import status

from fanfan.presentation.web.schemas.error import ErrorMessage, ValidationErrorResponse

# Validation can happen on any route that accepts input, so this set is applied
# globally in setup_api_router().
VALIDATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ValidationErrorResponse,
        "description": "Request validation error.",
    },
}

# Only attached to routes that require an authenticated user (alongside the
# SessionCookie security marker), so public routes no longer advertise 401/403.
AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorMessage,
        "description": "Not authenticated.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorMessage,
        "description": "Access denied.",
    },
}

# Attached to routes whose interactor takes a rate lock (e.g. schedule edits share
# the announcement cooldown), so the 429 + Retry-After contract is documented in
# one place instead of being repeated per route.
RATE_LIMIT_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorMessage,
        "description": "Rate limited — editing too fast.",
        "headers": {
            "Retry-After": {
                "schema": {"type": "integer"},
                "description": "Seconds to wait before retrying.",
            }
        },
    },
}
