import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.ticketscloud.sync_tcloud import SyncTCloud
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
        sync_tcloud = await r_container.get(SyncTCloud)
        await sync_tcloud()
        logger.info("Importing from TCloud done!")
