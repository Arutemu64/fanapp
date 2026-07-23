import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.tickets.sync_tickets import SyncTickets
from fanfan.core.vo.sync import SyncTrigger
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
        sync_tickets = await r_container.get(SyncTickets)
        await sync_tickets(trigger=SyncTrigger.CLI)
        logger.info("Importing from TCloud done!")
