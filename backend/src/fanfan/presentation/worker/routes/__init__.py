from fanfan.presentation.worker.router import JobRouter
from fanfan.presentation.worker.routes.notifications import notifications_router
from fanfan.presentation.worker.routes.schedule import schedule_router
from fanfan.presentation.worker.routes.sync import sync_router


def setup_router() -> JobRouter:
    router = JobRouter()

    router.include(notifications_router)
    router.include(schedule_router)
    router.include(sync_router)

    return router
