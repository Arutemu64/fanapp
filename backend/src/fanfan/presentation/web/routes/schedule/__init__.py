from fanfan.presentation.web.routes.schedule.base import schedule_router
from fanfan.presentation.web.routes.schedule.changes import changes_router
from fanfan.presentation.web.routes.schedule.importing import importing_router
from fanfan.presentation.web.routes.schedule.management import management_router
from fanfan.presentation.web.routes.schedule.public import public_router
from fanfan.presentation.web.routes.schedule.subscriptions import subscriptions_router

PREFIX = "/schedule"

schedule_router.include_router(public_router, prefix=PREFIX)
schedule_router.include_router(importing_router, prefix=PREFIX)
schedule_router.include_router(management_router, prefix=PREFIX)
schedule_router.include_router(changes_router, prefix=PREFIX)
schedule_router.include_router(subscriptions_router, prefix=PREFIX)

__all__ = ["schedule_router"]
