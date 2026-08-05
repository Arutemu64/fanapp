import logging
from typing import TYPE_CHECKING

import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.application.interactors.demo.seed_demo_data import SeedDemoData
from fanfan.presentation.cli.commands.common import async_command

if TYPE_CHECKING:
    from dishka import AsyncContainer

logger = logging.getLogger(__name__)


@click.command(name="seed")
@click.pass_context
@async_command
async def seed_demo_command(context: click.Context):
    container: AsyncContainer = context.meta[CONTAINER_NAME]
    async with container() as r_container:
        seed_demo_data = await r_container.get(SeedDemoData)
        await seed_demo_data()
        logger.info("Demo data seeded!")
