import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from fanfan.presentation.web.routes.schedule import schedule_router

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_settings_path_is_not_taken_for_an_event_id(method: str) -> None:
    app = FastAPI()
    app.include_router(schedule_router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.request(method, "/schedule/settings", json={})

    assert "event_id" not in response.text
