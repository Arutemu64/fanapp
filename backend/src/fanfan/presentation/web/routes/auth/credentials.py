from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Form, Request, Response
from pydantic import BaseModel, EmailStr, Field
from starlette import status

from fanfan.application.interactors.auth.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserInput,
)
from fanfan.core.vo.fields import PASSWORD_MAX_LENGTH
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.responses import RATE_LIMIT_RESPONSES
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.utils import get_client_ip


class EmailPasswordLoginForm(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH, repr=False)


credentials_router = APIRouter()


@credentials_router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Login and create session",
    description="Authenticates user with email and password. "
    "Sets an HttpOnly cookie with an opaque session id.",
    responses={
        204: {"description": "Successfully authenticated. Session cookie is set."},
        **RATE_LIMIT_RESPONSES,
        401: {"model": ProblemDetails, "description": "Invalid email or password."},
    },
)
@inject
async def login(
    request: Request,
    form_data: Annotated[EmailPasswordLoginForm, Form()],
    interactor: FromDishka[AuthenticateUser],
    config: FromDishka[WebConfig],
    response: Response,
) -> None:
    session_id = await interactor(
        AuthenticateUserInput(
            email=form_data.email,
            password=form_data.password,
            client_ip=get_client_ip(request),
        )
    )

    set_auth_cookie(response, session_id, config)
