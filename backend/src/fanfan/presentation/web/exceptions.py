from fastapi import HTTPException, Request, status
from starlette.responses import JSONResponse

from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.presentation.web.schemas.error import ErrorMessage


def clear_auth_cookies(response: JSONResponse) -> JSONResponse:
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


async def access_denied_handler(request: Request, exc: AccessDenied) -> JSONResponse:
    error_content = ErrorMessage(detail=exc.message).model_dump()
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=error_content)


async def user_not_authenticated_handler(
    request: Request, exc: UserNotAuthenticated
) -> JSONResponse:
    error_content = ErrorMessage(detail=exc.message).model_dump()
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_content,
    )
    return clear_auth_cookies(response)


async def auth_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return clear_auth_cookies(response)

    return response
