import logging

import click
from pydantic import ValidationError

from fanfan.application.interactors.users.create_user import (
    CreateUser,
    CreateUserInput,
)
from fanfan.core.exceptions.base import AppException
from fanfan.core.vo.user import UserRole
from fanfan.presentation.cli.commands.common import async_command, cli_container

logger = logging.getLogger(__name__)

_ROLE_CHOICE = click.Choice([r.value for r in UserRole])


@click.command(name="create")
@click.argument("username")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
)
@click.option("--role", type=_ROLE_CHOICE, default=UserRole.ORGANIZER.value)
@click.pass_context
@async_command
async def create_user_command(
    context: click.Context, username: str, password: str, role: str
) -> None:
    try:
        data = CreateUserInput(
            username=username, password=password, role=UserRole(role)
        )
    except ValidationError as err:
        problems = "\n".join(
            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
            for issue in err.errors()
        )
        raise click.ClickException(problems) from err

    container = cli_container(context)
    async with container() as r_container:
        create_user = await r_container.get(CreateUser)
        try:
            user = await create_user(data)
        except AppException as err:
            raise click.ClickException(err.code) from err
        logger.info(
            "Created user %s (%s) with id %s", user.username, user.role, user.id
        )
