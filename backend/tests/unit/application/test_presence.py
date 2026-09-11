import pytest

from fanfan.application.interactors.presence.get_online_users_count import (
    GetOnlineUsersCount,
)
from fanfan.application.interactors.presence.record_presence import RecordPresence
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId, Username, UserRole, generate_user_id

pytestmark = pytest.mark.unit


def _make_user() -> User:
    return User.create(
        id=generate_user_id(),
        username=Username("organizer"),
        hashed_password=None,
        role=UserRole.ORG,
    )


class _FakeCurrentUser:
    def __init__(self, user: User | None = None, user_id: UserId | None = None) -> None:
        self._user = user
        self._user_id = user_id

    async def require_user(self) -> User:
        assert self._user is not None
        return self._user

    async def get_user_id(self) -> UserId | None:
        return self._user_id


class _RecordingPresence:
    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.marked: list[UserId] = []

    async def mark_online(self, user_id: UserId) -> None:
        self.marked.append(user_id)

    async def count_online(self) -> int:
        return self.count


class _AllowPermissions:
    def __init__(self) -> None:
        self.checked: list[Permission] = []

    async def ensure(
        self,
        *,
        user: User,  # noqa: ARG002  # part of the PermissionService contract
        permission: Permission,
    ) -> None:
        self.checked.append(permission)


class _DenyPermissions:
    async def ensure(
        self,
        *,
        user: User,  # noqa: ARG002  # part of the PermissionService contract
        permission: Permission,  # noqa: ARG002  # part of the PermissionService contract
    ) -> None:
        raise AccessDenied


async def test_count_returns_presence_total_for_permitted_org() -> None:
    perms = _AllowPermissions()
    interactor = GetOnlineUsersCount(
        presence_gateway=_RecordingPresence(count=7),
        current_user_provider=_FakeCurrentUser(user=_make_user()),
        perm_service=perms,
    )

    result = await interactor()

    assert result.count == 7
    # The stat rides on the users:read grant, not a dedicated permission.
    assert perms.checked == [Permission.USERS_READ]


async def test_count_denied_without_users_read() -> None:
    interactor = GetOnlineUsersCount(
        presence_gateway=_RecordingPresence(count=7),
        current_user_provider=_FakeCurrentUser(user=_make_user()),
        perm_service=_DenyPermissions(),
    )

    with pytest.raises(AccessDenied):
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
