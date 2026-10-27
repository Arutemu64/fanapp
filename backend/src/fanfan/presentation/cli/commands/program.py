import logging

import click

from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.presentation.cli.commands.common import async_command, cli_container

logger = logging.getLogger(__name__)


@click.command(name="cosplay2")
@click.pass_context
@async_command
async def sync_cosplay2_command(context: click.Context) -> None:
    container = cli_container(context)
    async with container() as r_container:
        execute_sync = await r_container.get(ExecuteCosplaySync)
        await execute_sync()
        logger.info("Importing from C2 done!")
