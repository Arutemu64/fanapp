from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, status

from fanfan.application.dto.sync import SyncStatusDTO
from fanfan.application.interactors.sync.get_sync_status import GetSyncStatus
from fanfan.application.interactors.sync.run_sync import RunSync, RunSyncInput
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

sync_router = APIRouter(
    tags=["Sync"],
    prefix="/sync",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@sync_router.get(
    "/status",
    summary="Get external sync status",
    description=(
        "Returns, per external source (Cosplay2, TicketsCloud), the timestamp "
        "of the last successful sync and the most recent runs. Requires the "
        "'sync:run' permission."
    ),
)
@inject
async def get_sync_status(
    interactor: FromDishka[GetSyncStatus],
) -> SyncStatusDTO:
    return await interactor()


@sync_router.post(
    "/run",
    summary="Run an external sync",
    description=(
        "Runs a Cosplay2 or TicketsCloud sync immediately and records it in "
        "the run log. Requires the 'sync:run' permission. The run executes "
        "synchronously; refresh the status afterwards."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        429: {
            "model": ErrorMessage,
            "description": "A sync for this source is already running "
            "or was finished moments ago.",
        },
    },
)
@inject
async def run_sync(
    data: RunSyncInput,
    interactor: FromDishka[RunSync],
) -> None:
    await interactor(data)
