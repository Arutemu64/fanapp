from fanfan.presentation.web.routes.schedule.base import schedule_router
from fanfan.presentation.web.routes.schedule.changes import changes_router
from fanfan.presentation.web.routes.schedule.importing import importing_router
from fanfan.presentation.web.routes.schedule.management import management_router
from fanfan.presentation.web.routes.schedule.public import public_router
from fanfan.presentation.web.routes.schedule.subscriptions import subscriptions_router

# Routes match in registration order, so the static /import and /settings
# paths go ahead of management's /{event_id}, which would otherwise claim them
# and reject the segment as a malformed UUID.
#
# The prefix goes on each include, not on schedule_router: FastAPI refuses to
# include a router holding an empty-path route (GET /schedule itself) under an
# empty include prefix, whatever prefix the parent router carries.
PREFIX = "/schedule"

schedule_router.include_router(public_router, prefix=PREFIX)
schedule_router.include_router(importing_router, prefix=PREFIX)
schedule_router.include_router(management_router, prefix=PREFIX)
schedule_router.include_router(changes_router, prefix=PREFIX)
schedule_router.include_router(subscriptions_router, prefix=PREFIX)

__all__ = ["schedule_router"]
