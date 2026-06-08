from datetime import UTC, datetime, timezone

import pytest

from fanfan.core.events.users import EmailConfirmationCodeRequested
from fanfan.core.models.user import User
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
        email="alice@example.com",
    )

    assert user.id == user_id
    assert user.username == "alice"
    assert user.hashed_password == "hash"
    assert user.role == UserRole.ORG
    assert user.email == "alice@example.com"
    assert user.pending_email is None
    assert user.email_verified_at is None


def test_request_email_change_sets_pending_and_records_event():
    user = _user()

    user.request_email_change("new@example.com")

    assert user.pending_email == "new@example.com"
    assert user.pull_events() == [EmailConfirmationCodeRequested(user_id=user.id)]


def test_confirm_pending_email_promotes_pending_to_email():
    verified_at = datetime(2026, 6, 8, tzinfo=UTC)
    user = _user(email="old@example.com", pending_email="new@example.com")

    user.confirm_pending_email(verified_at)

    assert user.email == "new@example.com"
    assert user.pending_email is None
    assert user.email_verified_at == verified_at


def test_users_are_equal_by_id():
    user_id = generate_user_id()
    one = _user(id=user_id, username=Username("one"))
    two = _user(id=user_id, username=Username("two"))
    other = _user()

    assert one == two
    assert one != other
    # Equal users must share a hash so they collapse in sets/dicts.
    assert len({one, two}) == 1
