from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Response, status

from fanfan.application.dto.sync import SyncRunDTO, SyncSourceStatusDTO
from fanfan.application.interactors.sync.get_sync_sources import GetSyncSources
from fanfan.application.interactors.sync.request_sync import (
    RequestSync,
    RequestSyncInput,
)
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

sync_router = APIRouter(
    tags=["Sync"],
    prefix="/sync",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)

# The 202's status resource. There is no per-run endpoint: nothing polls a
# single run — the page loads this list and is pushed updates over SSE — and it
# already reports the active run for each source.
SYNC_STATUS_PATH = "/sync/sources"


@sync_router.get(
    "/sources",
    summary="List sync sources with their last run",
    description=(
        "Returns every vendor sync source, whether it is configured for this "
        "deployment, and its most recent run. Requires the 'sync:run' permission."
    ),
)
@inject
async def get_sync_sources(
    interactor: FromDishka[GetSyncSources],
) -> list[SyncSourceStatusDTO]:
    return await interactor()


@sync_router.post(
    "/{source}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a sync",
    description=(
        "Queues a sync of the given source and returns immediately with the "
        "created run. The work runs in the stream service, so progress arrives "
        "over SSE ('sync_run_updated') and the run's final state is readable "
        "from GET /sync/sources. Requires the 'sync:run' permission."
    ),
    responses={
        202: {
            "model": SyncRunDTO,
            "description": "Sync queued; poll GET /sync/sources for its state.",
        },
        409: {
            "model": ErrorMessage,
            "description": "A sync for this source is already running.",
        },
    },
)
@inject
async def request_sync(
    source: SyncSource,
    response: Response,
    interactor: FromDishka[RequestSync],
) -> SyncRunDTO:
    run = await interactor(RequestSyncInput(source=source))
    response.headers["Location"] = SYNC_STATUS_PATH
    return run
