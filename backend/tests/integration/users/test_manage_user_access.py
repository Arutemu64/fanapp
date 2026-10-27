from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.users.set_user_permission import (
    SetUserPermission,
    SetUserPermissionInput,
)
from fanfan.application.interactors.users.set_user_role import (
    SetUserRole,
    SetUserRoleInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import CannotChangeOwnAccess, PermissionNotAssignable
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_users_manager_changes_role(
    dishka_request: AsyncContainer,
    users_manager: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserRole)
    user_gateway = await dishka_request.get(UserGateway)
    login(users_manager)

    await interactor(SetUserRoleInput(user_id=visitor.id, role=UserRole.VOLUNTEER))

    changed = await user_gateway.get_by_id(visitor.id)
    assert changed is not None
    assert changed.role is UserRole.VOLUNTEER


async def test_role_change_requires_users_manage(
    dishka_request: AsyncContainer,
    users_reader: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserRole)
    login(users_reader)

    with pytest.raises(AccessDenied):
        await interactor(SetUserRoleInput(user_id=visitor.id, role=UserRole.ORGANIZER))


async def test_cannot_change_own_role(
    dishka_request: AsyncContainer,
    users_manager: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserRole)
    login(users_manager)

    with pytest.raises(CannotChangeOwnAccess):
        await interactor(
            SetUserRoleInput(user_id=users_manager.id, role=UserRole.VISITOR)
        )


async def test_superuser_grants_and_revokes(
    dishka_request: AsyncContainer,
    superuser: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserPermission)
    perm_gateway = await dishka_request.get(UserPermissionGateway)
    login(superuser)

    for _ in range(2):
        await interactor(
            SetUserPermissionInput(
                user_id=visitor.id, permission=Permission.FEEDBACK_READ, granted=True
            )
        )
    granted = await perm_gateway.get_all_for_user(visitor.id)
    assert [p.permission for p in granted] == [Permission.FEEDBACK_READ]

    for _ in range(2):
        await interactor(
            SetUserPermissionInput(
                user_id=visitor.id, permission=Permission.FEEDBACK_READ, granted=False
            )
        )
    assert await perm_gateway.get_all_for_user(visitor.id) == []


async def test_permission_change_requires_superuser(
    dishka_request: AsyncContainer,
    users_manager: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserPermission)
    login(users_manager)

    with pytest.raises(AccessDenied):
        await interactor(
            SetUserPermissionInput(
                user_id=visitor.id, permission=Permission.USERS_READ, granted=True
            )
        )


async def test_wildcard_is_not_assignable(
    dishka_request: AsyncContainer,
    superuser: User,
    visitor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserPermission)
    login(superuser)

    with pytest.raises(PermissionNotAssignable):
        await interactor(
            SetUserPermissionInput(
                user_id=visitor.id, permission=Permission.WILDCARD, granted=True
            )
        )


async def test_cannot_change_own_permissions(
    dishka_request: AsyncContainer,
    superuser: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(SetUserPermission)
    login(superuser)

    with pytest.raises(CannotChangeOwnAccess):
        await interactor(
            SetUserPermissionInput(
                user_id=superuser.id, permission=Permission.USERS_READ, granted=False
            )
        )
