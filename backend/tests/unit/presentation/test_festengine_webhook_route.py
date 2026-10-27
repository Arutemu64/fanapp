import json
import time

import pytest
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from pydantic import SecretStr
from starlette.testclient import TestClient

from fanfan.application.interactors.festengine.handle_festengine_event import (
    FestEngineAction,
    FestEngineEventInput,
    FestEngineEventOutput,
    FestEngineEventStatus,
    HandleFestEngineEvent,
)
from fanfan.presentation.web.exceptions import add_exception_handlers
from fanfan.presentation.web.festengine import FestEngineConfig, sign
from fanfan.presentation.web.routes.webhooks import webhooks_router

pytestmark = pytest.mark.unit

SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
MSG_ID = "msg_2b1a"
URL = "/webhooks/festengine"
ROW_PLAY = {
    "type": "row.play",
    "timestamp": "2026-10-09T11:03:12.481Z",
    "data": {
        "num": "183",
        "grid_num": "183",
        "row_type": "track",
        "fields": {"name": "Naruto — Sasuke"},
        "notes": "",
    },
}


class _RecordEvents:
    def __init__(self) -> None:
        self.received: list[FestEngineEventInput] = []

    async def __call__(self, data: FestEngineEventInput) -> FestEngineEventOutput:
        self.received.append(data)
        return FestEngineEventOutput(
            status=FestEngineEventStatus.UPDATED,
            actions=[FestEngineAction.SET_CURRENT],
        )


def _client(recorder: _RecordEvents, secret: str | None) -> TestClient:
    config = FestEngineConfig(webhook_secret=SecretStr(secret) if secret else None)
    provider = Provider(scope=Scope.REQUEST)
    provider.provide(lambda: recorder, provides=HandleFestEngineEvent)
    provider.provide(lambda: config, provides=FestEngineConfig)
    app = FastAPI()
    app.include_router(webhooks_router)
    add_exception_handlers(app)
    setup_dishka(make_async_container(provider), app)
    return TestClient(app)


def _signed_headers(body: bytes, timestamp: int | None = None) -> dict[str, str]:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    return {
        "content-type": "application/json",
        "webhook-id": MSG_ID,
        "webhook-timestamp": ts,
        "webhook-signature": sign(SECRET, MSG_ID, ts, body),
    }


def test_signed_event_reaches_the_interactor() -> None:
    recorder = _RecordEvents()
    body = json.dumps(ROW_PLAY, ensure_ascii=False).encode()

    with _client(recorder, SECRET) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 200
    assert response.json() == {"status": "updated", "actions": ["set_current"]}
    assert len(recorder.received) == 1
    assert recorder.received[0].type == "row.play"
    assert recorder.received[0].data.num == "183"


def test_endpoint_is_hidden_without_a_secret() -> None:
    recorder = _RecordEvents()
    body = json.dumps(ROW_PLAY).encode()

    with _client(recorder, None) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 404
    assert recorder.received == []


def test_bad_signature_is_hidden_as_404() -> None:
    recorder = _RecordEvents()
    body = json.dumps(ROW_PLAY).encode()
    headers = _signed_headers(body)
    headers["webhook-signature"] = "v1,AAAA"

    with _client(recorder, SECRET) as client:
        response = client.post(URL, content=body, headers=headers)

    assert response.status_code == 404
    assert recorder.received == []


def test_replayed_request_is_hidden_as_404() -> None:
    recorder = _RecordEvents()
    body = json.dumps(ROW_PLAY).encode()
    headers = _signed_headers(body, timestamp=int(time.time()) - 600)

    with _client(recorder, SECRET) as client:
        response = client.post(URL, content=body, headers=headers)

    assert response.status_code == 404


def test_unsigned_request_is_hidden_as_404() -> None:
    recorder = _RecordEvents()
    body = json.dumps(ROW_PLAY).encode()

    with _client(recorder, SECRET) as client:
        response = client.post(
            URL, content=body, headers={"content-type": "application/json"}
        )

    assert response.status_code == 404


def test_signed_but_malformed_body_is_rejected_as_422() -> None:
    recorder = _RecordEvents()
    body = b'{"type": "row.play"}'

    with _client(recorder, SECRET) as client:
        response = client.post(URL, content=body, headers=_signed_headers(body))

    assert response.status_code == 422
    assert recorder.received == []
