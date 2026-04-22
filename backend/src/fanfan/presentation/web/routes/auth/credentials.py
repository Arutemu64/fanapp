from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Form, Response
from pydantic import BaseModel, EmailStr, Field
from starlette import status

from fanfan.application.dto.user import UserBaseDTO
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


class EmailPasswordLoginForm(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    @classmethod
    def as_form(
        cls,
        email: Annotated[EmailStr, Form(...)],
        password: Annotated[str, Form(...)],
    ) -> "EmailPasswordLoginForm":
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
    },
)
@inject
async def login(
    form_data: Annotated[
        EmailPasswordLoginForm, Depends(EmailPasswordLoginForm.as_form)
    ],
    interactor: FromDishka[AuthenticateUser],
    config: FromDishka[WebConfig],
    response: Response,
) -> None:
    # Keep login flow explicit so junior developers can follow each step.
    session_id = await interactor(
        AuthenticateUserInput(email=form_data.email, password=form_data.password)
    )

    set_auth_cookie(response, session_id, config)


@credentials_router.post(
    "/register",
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account with an email and password. "
    "A username is generated automatically.",
    responses={
        201: {"model": UserBaseDTO, "description": "User successfully registered."},
        409: {
            "model": ErrorMessage,
            "description": "Conflict: username or email already in use.",
        },
    },
)
@inject
async def register_user(
    data: RegisterUserInput,
    interactor: FromDishka[RegisterUser],
) -> None:
    return await interactor(data)
