from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Form, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from starlette import status

from fanfan.application.auth.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
)
from fanfan.application.auth.register_user import RegisterUser, RegisterUserCommand
from fanfan.core.dto.user import UserBaseDTO
from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.exceptions.users import UserAlreadyExists, UserNotFound
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookies
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
    summary="Login and get access token",
    description="Authenticates user with email and password. "
    "Sets HttpOnly cookies with JWT access and refresh tokens.",
    responses={
        204: {"description": "Successfully authenticated. Tokens set in cookies."},
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
    try:
        token = await interactor(
            AuthenticateUserCommand(email=form_data.email, password=form_data.password)
        )
    except (UserNotFound, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    set_auth_cookies(response, token.access_token, token.refresh_token, config)


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
    data: RegisterUserCommand,
    interactor: FromDishka[RegisterUser],
) -> None:
    try:
        result = await interactor(data)
    except UserAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    return result
