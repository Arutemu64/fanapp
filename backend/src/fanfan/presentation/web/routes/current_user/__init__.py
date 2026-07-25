from fanfan.presentation.web.routes.current_user.base import current_user_router
from fanfan.presentation.web.routes.current_user.connections import connections_router
from fanfan.presentation.web.routes.current_user.profile import profile_router
from fanfan.presentation.web.routes.current_user.security import security_router
from fanfan.presentation.web.routes.current_user.tickets import tickets_router

current_user_router.include_router(profile_router)
current_user_router.include_router(security_router)
current_user_router.include_router(connections_router)
current_user_router.include_router(tickets_router)

__all__ = ["current_user_router"]
