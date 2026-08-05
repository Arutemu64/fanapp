import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.cli.commands.demo import seed_demo_command
from fanfan.presentation.cli.commands.program import sync_cosplay2_command
from fanfan.presentation.cli.commands.tickets import sync_tcloud_command


@click.group()
@click.pass_context
def cli(context: click.Context):
    # No setup_dishka in there because it doesn't support async containers
    context.meta[CONTAINER_NAME] = create_system_container()


@click.group(name="sync")
def sync_group():
    """Run external syncs."""


@click.group(name="demo")
def demo_group():
    """Populate the environment with demo data."""


def main():
    init(service_name="cli")

    sync_group.add_command(sync_cosplay2_command)
    sync_group.add_command(sync_tcloud_command)

    demo_group.add_command(seed_demo_command)

    cli.add_command(sync_group)
    cli.add_command(demo_group)

    cli()


if __name__ == "__main__":
    main()
