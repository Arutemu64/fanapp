from faststream.nats import NatsRouter

from fanfan.presentation.faststream.routes.notifications import notifications_router
from fanfan.presentation.faststream.routes.schedule import schedule_router
from fanfan.presentation.faststream.routes.sync import sync_router
from fanfan.presentation.faststream.routes.users import users_router
from fanfan.presentation.faststream.routes.voting import voting_router


def setup_router() -> NatsRouter:
    router = NatsRouter()

    router.include_router(notifications_router)
    router.include_router(schedule_router)
    router.include_router(voting_router)
    router.include_router(users_router)
    router.include_router(sync_router)

    return router
