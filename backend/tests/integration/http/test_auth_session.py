from http import HTTPStatus

from dishka import AsyncContainer
from httpx2 import AsyncClient

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.password_hasher import PasswordHasher
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id
from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME

EMAIL = "attendee@example.com"
PASSWORD = "correct-horse-battery"


async def _user_with_password(dishka_request: AsyncContainer) -> User:
    user_gateway = await dishka_request.get(UserGateway)
    password_hasher = await dishka_request.get(PasswordHasher)
    uow = await dishka_request.get(UnitOfWork)
    user = User(
        id=generate_user_id(),
        username=Username("attendee"),
        email=Email(EMAIL),
        hashed_password=await password_hasher.hash(PASSWORD),
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    await uow.commit()
    return user


async def test_login_session_survives_requests_until_logout_revokes_it(
    dishka_request: AsyncContainer, client: AsyncClient
) -> None:
    user = await _user_with_password(dishka_request)

    login = await client.post(
        "/auth/login", data={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == HTTPStatus.NO_CONTENT
    assert "httponly" in login.headers["set-cookie"].lower()
    session_id = client.cookies[SESSION_COOKIE_NAME]

    me = await client.get("/me")
    assert me.status_code == HTTPStatus.OK
    assert me.json()["id"] == str(user.id)

    logout = await client.post("/auth/logout")
    assert logout.status_code == HTTPStatus.NO_CONTENT

    # Replaying the old cookie proves the server dropped the session,
    # not just the browser.
    client.cookies.set(SESSION_COOKIE_NAME, session_id)
    replay = await client.get("/me")
    assert replay.status_code == HTTPStatus.UNAUTHORIZED


async def test_wrong_password_is_a_401_problem_without_a_cookie(
    dishka_request: AsyncContainer, client: AsyncClient
) -> None:
    await _user_with_password(dishka_request)

    response = await client.post(
        "/auth/login", data={"email": EMAIL, "password": "wrong-password"}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert SESSION_COOKIE_NAME not in client.cookies


async def test_anonymous_request_is_a_401_problem(client: AsyncClient) -> None:
    response = await client.get("/me")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "USER_NOT_AUTHENTICATED"
