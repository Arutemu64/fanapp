import asyncio
import contextlib
import logging

from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.adapters.db.gateways.permissions import PermissionGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.constants.permissions import Permissions
from fanfan.core.models.app_settings import AppSettings
from fanfan.core.models.permission import Permission
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.main.common import init
from fanfan.main.di import create_system_container

logger = logging.getLogger(__name__)


async def migrate():
    container = create_system_container()
    async with container() as container:
        uow = await container.get(UnitOfWork)

        # Create system user
        user_gateway = await container.get(UserGateway)
        system_user = User(
            id=UserId(0),
            username=Username("system"),
            tg_id=None,
            first_name=None,
            last_name=None,
            role=UserRole.ORG,
            settings=UserSettings(),
            hashed_password=None,
        )
        await user_gateway.save_user(system_user)
        logger.info("System user created")

        # Add new permissions
        permission_gateway = await container.get(PermissionGateway)
        for name in Permissions:
            try:
                async with uow.nested():
                    await permission_gateway.add_permission(Permission(name=name))
                    logger.info("New permission added: %s", name)
            except IntegrityError:
                logger.info("Permission %s already exist", name)

        # Setup initial settings
        settings_gateway = await container.get(SettingsGateway)
        try:
            async with uow.nested():
                await settings_gateway.add_settings(AppSettings())
                logger.info("Settings added")
        except IntegrityError:
            logger.info("Settings already exist")

        await uow.commit()
    logger.info("Migration completed")


def main():
    init(service_name="migration")
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(migrate())


if __name__ == "__main__":
    main()
