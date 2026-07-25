import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.presentation.cli.commands.common import async_command

if TYPE_CHECKING:
    from dishka import AsyncContainer

logger = logging.getLogger(__name__)


@click.command(name="tcloud")
@click.pass_context
@async_command
async def sync_tcloud_command(context: click.Context):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        # Execute*Sync, not the bare interactor, so a CLI run is recorded in
        # sync_runs like any other trigger.
        execute_sync = await r_container.get(ExecuteTicketsSync)
        await execute_sync()
        logger.info("Importing from TCloud done!")
