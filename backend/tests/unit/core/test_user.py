import pytest

from fanfan.core.models.user import User
from fanfan.core.vo.email import Email
from fanfan.core.vo.user import Username, UserRole, generate_user_id

pytestmark = pytest.mark.unit


def _user(**overrides) -> User:
    defaults = {
        "id": generate_user_id(),
        "username": Username("tester"),
        "hashed_password": None,
        "role": UserRole.VISITOR,
    }
    defaults.update(overrides)
    return User.create(**defaults)


def test_create_sets_given_fields():
    user_id = generate_user_id()

    user = User.create(
        id=user_id,
        username=Username("alice"),
        hashed_password="hash",
        role=UserRole.ORG,
        email=Email("alice@example.com"),
    )

    assert user.id == user_id
    assert user.username == "alice"
    assert user.hashed_password == "hash"
    assert user.role == UserRole.ORG
    assert user.email == Email("alice@example.com")


def test_set_email_updates_email():
    user = _user()

    user.set_email(Email("new@example.com"))

    assert user.email == Email("new@example.com")


def test_users_are_equal_by_id():
    user_id = generate_user_id()
    one = _user(id=user_id, username=Username("one"))
    two = _user(id=user_id, username=Username("two"))
    other = _user()

    assert one == two
    assert one != other
    # Equal users must share a hash so they collapse in sets/dicts.
    assert len({one, two}) == 1
