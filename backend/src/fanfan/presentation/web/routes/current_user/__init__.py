from fanfan.presentation.web.routes.current_user.base import current_user_router
from fanfan.presentation.web.routes.current_user.connections import connections_router
from fanfan.presentation.web.routes.current_user.profile import profile_router
from fanfan.presentation.web.routes.current_user.security import security_router
from fanfan.presentation.web.routes.current_user.tickets import tickets_router

# The prefix goes on each include, not on current_user_router: FastAPI refuses
# to include a router holding an empty-path route (GET /me itself) under an empty
# include prefix, whatever prefix the parent router carries.
PREFIX = "/me"

current_user_router.include_router(profile_router, prefix=PREFIX)
current_user_router.include_router(security_router, prefix=PREFIX)
current_user_router.include_router(connections_router, prefix=PREFIX)
current_user_router.include_router(tickets_router, prefix=PREFIX)

__all__ = ["current_user_router"]
