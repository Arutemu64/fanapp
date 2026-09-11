import pytest

from fanfan.application.interactors.presence.get_online_users_count import (
    GetOnlineUsersCount,
)
from fanfan.application.interactors.presence.record_presence import RecordPresence
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.vo.user import UserId, generate_user_id

pytestmark = pytest.mark.unit


class _FakeCurrentUser:
    def __init__(self, user_id: UserId | None = None) -> None:
        self._user_id = user_id

    async def get_user_id(self) -> UserId | None:
        return self._user_id

    async def require_user_id(self) -> UserId:
        if self._user_id is None:
            raise UserNotAuthenticated
        return self._user_id


class _RecordingPresence:
    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.marked: list[UserId] = []

    async def mark_online(self, user_id: UserId) -> None:
        self.marked.append(user_id)

    async def count_online(self) -> int:
        return self.count


async def test_count_returns_presence_total_for_authenticated_user() -> None:
    interactor = GetOnlineUsersCount(
        presence_gateway=_RecordingPresence(count=7),
        current_user_provider=_FakeCurrentUser(user_id=generate_user_id()),
    )

    result = await interactor()

    assert result.count == 7


async def test_count_requires_authentication() -> None:
    interactor = GetOnlineUsersCount(
        presence_gateway=_RecordingPresence(count=7),
        current_user_provider=_FakeCurrentUser(user_id=None),
    )

    with pytest.raises(UserNotAuthenticated):
        await interactor()


async def test_record_marks_authenticated_user_online() -> None:
    user_id = generate_user_id()
    presence = _RecordingPresence()
    interactor = RecordPresence(
        presence_gateway=presence,
        current_user_provider=_FakeCurrentUser(user_id=user_id),
    )

    await interactor()

    assert presence.marked == [user_id]


async def test_record_is_noop_for_anonymous_stream() -> None:
    presence = _RecordingPresence()
    interactor = RecordPresence(
        presence_gateway=presence,
        current_user_provider=_FakeCurrentUser(user_id=None),
    )

    await interactor()

    # An unauthenticated SSE connection has no user to count.
    assert presence.marked == []
