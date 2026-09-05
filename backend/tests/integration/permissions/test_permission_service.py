import pytest
from dishka import AsyncContainer

from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_ensure_passes_for_the_granted_permission(
    dishka_request: AsyncContainer,
    sync_operator: User,
):
    perm_service = await dishka_request.get(PermissionService)

    await perm_service.ensure(user=sync_operator, permission=Permission.SYNC_RUN)


async def test_ensure_denies_a_missing_permission(
    dishka_request: AsyncContainer,
    visitor: User,
):
    perm_service = await dishka_request.get(PermissionService)

    with pytest.raises(AccessDenied):
        await perm_service.ensure(user=visitor, permission=Permission.SYNC_RUN)


async def test_wildcard_passes_every_permission_check(
    dishka_request: AsyncContainer,
    superuser: User,
):
    perm_service = await dishka_request.get(PermissionService)

    # The superuser holds only "*", yet clears checks for every specific
    # permission it was never granted directly.
    for permission in Permission:
        await perm_service.ensure(user=superuser, permission=permission)
