import click
from dishka.integrations.click import CONTAINER_NAME

from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.cli.commands.demo import seed_demo_command
from fanfan.presentation.cli.commands.permissions import (
    grant_permission_command,
    list_permissions_command,
    revoke_permission_command,
)
from fanfan.presentation.cli.commands.program import sync_cosplay2_command
from fanfan.presentation.cli.commands.tickets import sync_tcloud_command
from fanfan.presentation.cli.commands.users import create_user_command


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


@click.group(name="permissions")
def permissions_group():
    """Grant, revoke and list per-user permissions."""


@click.group(name="users")
def users_group():
    """Manage user accounts."""


def main():
    init(service_name="cli")

    sync_group.add_command(sync_cosplay2_command)
    sync_group.add_command(sync_tcloud_command)

    demo_group.add_command(seed_demo_command)

    permissions_group.add_command(grant_permission_command)
    permissions_group.add_command(revoke_permission_command)
    permissions_group.add_command(list_permissions_command)

    users_group.add_command(create_user_command)

    cli.add_command(sync_group)
    cli.add_command(demo_group)
    cli.add_command(permissions_group)
    cli.add_command(users_group)

    cli()


if __name__ == "__main__":
    main()
