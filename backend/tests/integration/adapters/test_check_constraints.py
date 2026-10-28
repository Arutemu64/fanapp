"""The database rejects rows that bypass the domain's normalization."""

from uuid import uuid7

import pytest
from dishka import AsyncContainer
from sqlalchemy import Insert, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.models import UserORM

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _insert_user(email: str) -> Insert:
    user_id = uuid7()
    return insert(UserORM).values(
        id=user_id,
        username=f"ck-{user_id.hex[:8]}",
        avatar_seed="seed",
        number=int(user_id.int % 900_000) + 100_000,
        email=email,
    )


async def test_normalized_email_is_accepted(dishka_request: AsyncContainer) -> None:
    session = await dishka_request.get(AsyncSession)

    await session.execute(_insert_user("ann@example.com"))


@pytest.mark.parametrize("email", ["Ann@Example.com", " ann@example.com"])
async def test_unnormalized_email_is_rejected(
    dishka_request: AsyncContainer, email: str
) -> None:
    session = await dishka_request.get(AsyncSession)

    # The savepoint rolls back on the error, so the shared session stays usable.
    with pytest.raises(IntegrityError) as error:
        async with session.begin_nested():
            await session.execute(_insert_user(email))

    assert get_constraint_name(error.value) == "ck_users_email_normalized"
