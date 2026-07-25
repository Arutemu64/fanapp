from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Form, Request, Response
from pydantic import BaseModel, EmailStr
from starlette import status

from fanfan.application.interactors.auth.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserInput,
)
from fanfan.application.interactors.auth.register_user import (
    RegisterUser,
    RegisterUserInput,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.utils import get_client_ip


class EmailPasswordLoginForm(BaseModel):
    email: EmailStr
    password: str

    @classmethod
    def as_form(
        cls,
        email: Annotated[EmailStr, Form()],
        password: Annotated[str, Form()],
    ) -> EmailPasswordLoginForm:
        return cls(email=email, password=password)


credentials_router = APIRouter()


@credentials_router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Login and create session",
    description="Authenticates user with email and password. "
    "Sets an HttpOnly cookie with a Redis-backed session id.",
    responses={
        204: {"description": "Successfully authenticated. Session cookie is set."},
        401: {"model": ErrorMessage, "description": "Invalid email or password."},
        429: {
            "model": ErrorMessage,
            "description": "Too many login attempts. Try again later.",
        },
    },
)
@inject
async def login(
    request: Request,
    form_data: Annotated[
        EmailPasswordLoginForm, Depends(EmailPasswordLoginForm.as_form)
    ],
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


@credentials_router.post(
    "/register",
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account with an email and password. "
    "A username is generated automatically. To avoid leaking which emails "
    "already have an account, the response is the same whether the account "
    "was created or the email was already taken.",
    responses={
        201: {"description": "Registration request accepted."},
    },
)
@inject
async def register_user(
    data: RegisterUserInput,
    interactor: FromDishka[RegisterUser],
) -> None:
    await interactor(data)
