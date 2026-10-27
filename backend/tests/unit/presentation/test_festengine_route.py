import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from pydantic import SecretStr
from starlette.testclient import TestClient

from fanfan.application.interactors.schedule_mgmt.apply_stage_console_action import (
    ApplyStageConsoleAction,
    ApplyStageConsoleActionInput,
    StageConsoleAction,
)
from fanfan.presentation.web.exceptions import add_exception_handlers
from fanfan.presentation.web.festengine.config import FestEngineConfig
from fanfan.presentation.web.festengine.signature import sign
from fanfan.presentation.web.routes.webhooks import webhooks_router

pytestmark = pytest.mark.unit

# The public example secret from the Standard Webhooks test suites.
SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"  # gitleaks:allow
URL = "/webhooks/festengine"


class _RecordAction:
    def __init__(self, *, changed: bool) -> None:
        self.changed = changed
        self.received: list[ApplyStageConsoleActionInput] = []

    async def __call__(self, data: ApplyStageConsoleActionInput) -> bool:
        self.received.append(data)
        return self.changed


def _client(recorder: _RecordAction, secret: str | None = SECRET) -> TestClient:
    config = FestEngineConfig(
        webhook_secret=SecretStr(secret) if secret is not None else None
    )
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(lambda: recorder, provides=ApplyStageConsoleAction)
    provider.provide(lambda: config, provides=FestEngineConfig)
    app = FastAPI()
    app.include_router(webhooks_router)
    add_exception_handlers(app)
    setup_dishka(make_async_container(provider), app)
    return TestClient(app)


def _body(event_type: str, *, age: timedelta = timedelta()) -> bytes:
    payload: dict[str, Any] = {
        "type": event_type,
        "timestamp": (datetime.now(UTC) - age).isoformat(),
        "data": {
            "row": {"num": "116", "grid_num": "116", "row_type": "track"},
        },
    }
    return json.dumps(payload).encode()


def _signed_headers(body: bytes, secret: str = SECRET) -> dict[str, str]:
    timestamp = int(time.time())
    return {
        "content-type": "application/json",
        "webhook-id": "msg_1",
        "webhook-timestamp": str(timestamp),
        "webhook-signature": sign(secret, "msg_1", timestamp, body),
    }


def test_signed_show_sets_the_act_current() -> None:
    recorder = _RecordAction(changed=True)
    body = _body("row.show")

    with _client(recorder) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
    assert recorder.received == [
        ApplyStageConsoleActionInput(action=StageConsoleAction.SET_CURRENT, number=116)
    ]


def test_already_applied_answers_unchanged() -> None:
    body = _body("row.play")

    with _client(_RecordAction(changed=False)) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.json() == {"status": "unchanged"}


def test_unrelated_event_is_ignored() -> None:
    recorder = _RecordAction(changed=True)
    body = _body("row.updated")

    with _client(recorder) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.json() == {"status": "ignored"}
    assert recorder.received == []


def test_late_show_cue_is_stale() -> None:
    recorder = _RecordAction(changed=True)
    body = _body("row.show", age=timedelta(minutes=2))

    with _client(recorder) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.json() == {"status": "stale"}
    assert recorder.received == []


def test_without_a_configured_secret_the_route_is_not_found() -> None:
    body = _body("row.show")

    with _client(_RecordAction(changed=True), secret=None) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 404


@pytest.mark.parametrize("tamper", ["unsigned", "other_key", "edited_body"])
def test_unverified_request_is_not_found(tamper: str) -> None:
    recorder = _RecordAction(changed=True)
    body = _body("row.show")
    headers = _signed_headers(body)
    if tamper == "unsigned":
        del headers["webhook-signature"]
    if tamper == "other_key":
        headers = _signed_headers(body, secret="whsec_" + "A" * 43 + "=")
    if tamper == "edited_body":
        body = _body("row.skip")

    with _client(recorder) as client:
        response = client.post(URL, content=body, headers=headers)

    assert response.status_code == 404
    assert recorder.received == []


def test_malformed_payload_is_unprocessable() -> None:
    body = b'{"type": "row.show"}'

    with _client(_RecordAction(changed=True)) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 422
