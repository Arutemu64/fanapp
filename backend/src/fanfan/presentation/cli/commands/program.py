import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.cosplay.sync_cosplay import SyncCosplay
from fanfan.core.vo.sync import SyncTrigger
from fanfan.presentation.cli.commands.common import async_command

if TYPE_CHECKING:
    from dishka import AsyncContainer

logger = logging.getLogger(__name__)


@click.command(name="cosplay2")
@click.pass_context
@async_command
async def sync_cosplay2_command(context: click.Context):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        sync_cosplay = await r_container.get(SyncCosplay)
        await sync_cosplay(trigger=SyncTrigger.CLI)
        logger.info("Importing from C2 done!")
