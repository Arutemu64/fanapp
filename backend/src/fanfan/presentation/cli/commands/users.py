import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME
from pydantic import ValidationError

from fanfan.application.interactors.users.create_user import (
    CreateUser,
    CreateUserInput,
)
from fanfan.core.exceptions.base import AppException
from fanfan.core.vo.user import UserRole
from fanfan.presentation.cli.commands.common import async_command

if TYPE_CHECKING:
    from dishka import AsyncContainer

logger = logging.getLogger(__name__)

_ROLE_CHOICE = click.Choice([r.value for r in UserRole])


@click.command(name="create")
@click.argument("username")
# Prompt for the password instead of taking it as an argument so it never lands
# in shell history or the process table; confirm it to catch typos.
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
)
# Default to org: a CLI-created account is a staff account (the toolbox is
# org-only), and it is the natural companion to `permissions grant`. The role is
# only a UI label — it grants no access on its own — so permissions are still
# granted separately.
@click.option("--role", type=_ROLE_CHOICE, default=UserRole.ORG.value)
@click.pass_context
@async_command
async def create_user_command(
    context: click.Context, username: str, password: str, role: str
):
    try:
        data = CreateUserInput(
            username=username, password=password, role=UserRole(role)
        )
    except ValidationError as err:
        # Turn Pydantic's field errors (username pattern, password length) into a
        # clean CLI message instead of a traceback.
        raise click.ClickException(str(err)) from err

    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        create_user = await r_container.get(CreateUser)
        try:
            user = await create_user(data)
        except AppException as err:
            # Taken username, profanity — expected domain refusals, not bugs.
            # AppException stringifies to its stable code (USER_ALREADY_EXISTS, …).
            raise click.ClickException(err.code) from err
        logger.info(
            "Created user %s (%s) with id %s", user.username, user.role, user.id
        )
