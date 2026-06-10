from typing import Protocol

from fanfan.core.models.permission import Permission
from fanfan.core.vo.permission import PermissionName


class PermissionGateway(Protocol):
    async def get_by_name(
        self, permission_name: PermissionName
    ) -> Permission | None: ...
