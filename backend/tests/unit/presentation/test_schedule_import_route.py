import pytest
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.testclient import TestClient

from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.common.paths import REPO_ROOT
from fanfan.presentation.web.routes.schedule import schedule_router

pytestmark = pytest.mark.unit

TEMPLATE_PATH = REPO_ROOT / "frontend" / "static" / "schedule-template.xlsx"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _AnyUser:
    async def require_user(self) -> object:
        return object()


class _AllowAll:
    async def ensure(self, **_: object) -> None:
        return None


class _RecordImport:
    def __init__(self) -> None:
        self.received: list[ImportScheduleInput] = []

    async def __call__(self, data: ImportScheduleInput) -> None:
        self.received.append(data)


def test_import_reads_the_multipart_file_field_and_answers_204() -> None:
    """The multipart `file` field reaches the parser through ImportScheduleForm.

    The upload checks and the interactor have their own tests; this one covers
    FastAPI's extraction of the form model in between, which neither sees.
    """
    recorder = _RecordImport()
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(lambda: recorder, provides=ImportSchedule)
    provider.provide(_AnyUser, provides=CurrentUserProvider)
    provider.provide(_AllowAll, provides=PermissionService)
    app = FastAPI()
    app.include_router(schedule_router)
    setup_dishka(make_async_container(provider), app)

    with TestClient(app) as client:
        response = client.post(
            "/schedule/import",
            files={"file": ("schedule.xlsx", TEMPLATE_PATH.read_bytes(), XLSX_TYPE)},
        )

    assert response.status_code == 204
    assert response.content == b""
    assert len(recorder.received) == 1
    assert recorder.received[0].schedule
