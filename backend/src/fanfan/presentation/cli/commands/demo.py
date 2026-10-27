import logging

import click

from fanfan.application.interactors.demo.seed_demo_data import SeedDemoData
from fanfan.presentation.cli.commands.common import async_command, cli_container

logger = logging.getLogger(__name__)


@click.command(name="seed")
@click.pass_context
@async_command
async def seed_demo_command(context: click.Context) -> None:
    container = cli_container(context)
    async with container() as r_container:
        seed_demo_data = await r_container.get(SeedDemoData)
        await seed_demo_data()
        logger.info("Demo data seeded!")
