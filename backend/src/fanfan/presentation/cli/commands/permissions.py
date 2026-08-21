import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.permissions.grant_permission import (
    GrantPermission,
)
from fanfan.application.interactors.permissions.list_user_permissions import (
    ListUserPermissions,
)
from fanfan.application.interactors.permissions.revoke_permission import (
    RevokePermission,
)
from fanfan.core.vo.permission import Permission
from fanfan.presentation.cli.commands.common import async_command

if TYPE_CHECKING:
    from dishka import AsyncContainer

logger = logging.getLogger(__name__)

# The enum values ("schedule:manage", …) are the operator-facing choices, so a
# typo is rejected by click instead of silently failing the ensure() check later.
_PERMISSION_CHOICE = click.Choice([p.value for p in Permission])


@click.command(name="grant")
@click.argument("username")
@click.argument("permission", type=_PERMISSION_CHOICE)
@click.pass_context
@async_command
async def grant_permission_command(
    context: click.Context, username: str, permission: str
):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        grant = await r_container.get(GrantPermission)
        added = await grant(username=username, permission=Permission(permission))
        if added:
            logger.info("Granted %s to %s", permission, username)
        else:
            logger.info("%s already has %s, nothing to do", username, permission)


@click.command(name="revoke")
@click.argument("username")
@click.argument("permission", type=_PERMISSION_CHOICE)
@click.pass_context
@async_command
async def revoke_permission_command(
    context: click.Context, username: str, permission: str
):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        revoke = await r_container.get(RevokePermission)
        removed = await revoke(username=username, permission=Permission(permission))
        if removed:
            logger.info("Revoked %s from %s", permission, username)
        else:
            logger.info("%s does not have %s, nothing to do", username, permission)


@click.command(name="list")
@click.argument("username")
@click.pass_context
@async_command
async def list_permissions_command(context: click.Context, username: str):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        list_permissions = await r_container.get(ListUserPermissions)
        permissions = await list_permissions(username=username)
        if permissions:
            for permission in permissions:
                click.echo(permission.value)
        else:
            logger.info("%s has no permissions", username)
