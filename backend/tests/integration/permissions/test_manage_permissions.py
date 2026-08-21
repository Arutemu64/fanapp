import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.permissions.grant_permission import (
    GrantPermission,
)
from fanfan.application.interactors.permissions.list_user_permissions import (
    ListUserPermissions,
)
from fanfan.application.interactors.permissions.revoke_permission import (
    RevokePermission,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_grant_adds_the_permission(
    dishka_request: AsyncContainer,
    visitor: User,
):
    grant = await dishka_request.get(GrantPermission)
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    added = await grant(
        username=visitor.username, permission=Permission.SCHEDULE_MANAGE
    )

    assert added is True
    granted = await perm_gateway.get_by_permission(
        user_id=visitor.id, permission=Permission.SCHEDULE_MANAGE
    )
    assert granted is not None


async def test_grant_is_idempotent(
    dishka_request: AsyncContainer,
    visitor: User,
):
    grant = await dishka_request.get(GrantPermission)

    assert (
        await grant(username=visitor.username, permission=Permission.SCHEDULE_MANAGE)
        is True
    )
    # A second grant is a no-op — the unique (user, permission) row already exists.
    assert (
        await grant(username=visitor.username, permission=Permission.SCHEDULE_MANAGE)
        is False
    )


async def test_revoke_removes_the_permission(
    dishka_request: AsyncContainer,
    sync_operator: User,
):
    revoke = await dishka_request.get(RevokePermission)
    perm_gateway = await dishka_request.get(UserPermissionGateway)

    removed = await revoke(
        username=sync_operator.username, permission=Permission.SYNC_RUN
    )

    assert removed is True
    remaining = await perm_gateway.get_by_permission(
        user_id=sync_operator.id, permission=Permission.SYNC_RUN
    )
    assert remaining is None


async def test_revoke_without_the_grant_is_a_no_op(
    dishka_request: AsyncContainer,
    visitor: User,
):
    revoke = await dishka_request.get(RevokePermission)

    assert (
        await revoke(username=visitor.username, permission=Permission.SYNC_RUN) is False
    )


async def test_list_returns_granted_permissions(
    dishka_request: AsyncContainer,
    sync_operator: User,
):
    list_permissions = await dishka_request.get(ListUserPermissions)

    permissions = await list_permissions(username=sync_operator.username)

    assert permissions == [Permission.SYNC_RUN]


async def test_grant_rejects_unknown_user(dishka_request: AsyncContainer):
    grant = await dishka_request.get(GrantPermission)

    with pytest.raises(UserNotFound):
        await grant(username="ghost", permission=Permission.SCHEDULE_MANAGE)
