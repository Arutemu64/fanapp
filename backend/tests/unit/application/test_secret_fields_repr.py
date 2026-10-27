import pytest
from pydantic import BaseModel

from fanfan.application.interactors.auth.authenticate_user import AuthenticateUserInput
from fanfan.application.interactors.auth.change_password import ChangePasswordInput
from fanfan.application.interactors.auth.confirm_email_code import (
    ConfirmEmailCodeInput,
)
from fanfan.application.interactors.auth.login_with_code import LoginWithCodeInput
from fanfan.application.interactors.users.create_user import CreateUserInput
from fanfan.core.vo.user import UserRole
from fanfan.presentation.web.routes.auth.credentials import EmailPasswordLoginForm

pytestmark = pytest.mark.unit

PASSWORD = "correct-horse-battery"
CODE = "482915"


@pytest.mark.parametrize(
    ("model", "secret"),
    [
        (AuthenticateUserInput(email="a@example.com", password=PASSWORD), PASSWORD),
        (EmailPasswordLoginForm(email="a@example.com", password=PASSWORD), PASSWORD),
        (ChangePasswordInput(old_password=PASSWORD, new_password=PASSWORD), PASSWORD),
        (
            CreateUserInput(
                username="tester", password=PASSWORD, role=UserRole.VISITOR
            ),
            PASSWORD,
        ),
        (ConfirmEmailCodeInput(code=CODE), CODE),
        (LoginWithCodeInput(email="a@example.com", code=CODE), CODE),
    ],
)
def test_secret_stays_out_of_the_repr(model: BaseModel, secret: str) -> None:
    assert secret not in repr(model)
    assert secret not in str(model)
