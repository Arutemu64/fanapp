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


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(schedule_router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"is_skipped": None},
        {"is_skipped": True, "place_after_entry_id": None},
        {"place_after_entry_id": None, "is_skippped": True},
    ],
)
def test_event_update_takes_exactly_one_change(body: dict[str, object]) -> None:
    event_id = "01890a5d-ac96-774b-bcce-b302099a8057"

    response = _client().patch(f"/schedule/{event_id}", json=body)

    assert response.status_code == 422


def test_move_has_no_route_of_its_own() -> None:
    event_id = "01890a5d-ac96-774b-bcce-b302099a8057"

    response = _client().patch(f"/schedule/{event_id}/move", json={})

    assert response.status_code == 404


def test_set_current_takes_the_event_in_the_body() -> None:
    response = _client().put("/schedule/current", json={})

    assert response.status_code == 422
    assert "event_id" in response.text
