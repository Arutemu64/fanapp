from collections.abc import Callable
from dataclasses import dataclass

import httpx2
import pytest
from adaptix import Retort

from fanfan.adapters.api.base import MAX_ATTEMPTS, BaseApiClient
from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.dto.order import OrderStatus


@dataclass
class _Payload:
    value: int


type _Outcome = httpx2.Response | Exception


class _ScriptedHandler:
    """MockTransport handler that replays a scripted sequence of outcomes.

    One outcome is consumed per request — a Response is returned, an Exception
    is raised (to stand in for a transport-level timeout). The last outcome
    repeats once the script is exhausted, so a run that keeps failing keeps
    seeing the same error.
    """

    def __init__(self, outcomes: list[_Outcome]) -> None:
        self._outcomes = outcomes
        self.calls = 0

    def __call__(
        self,
        request: httpx2.Request,  # noqa: ARG002  # required by the MockTransport handler contract
    ) -> httpx2.Response:
        outcome = self._outcomes[min(self.calls, len(self._outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _ok(value: int) -> httpx2.Response:
    return httpx2.Response(200, json={"value": value})


def _status(code: int) -> httpx2.Response:
    return httpx2.Response(code, json={})


def _timeout() -> httpx2.ReadTimeout:
    return httpx2.ReadTimeout("vendor read timed out")


def _client(handler: _ScriptedHandler) -> BaseApiClient:
    http = httpx2.AsyncClient(
        transport=httpx2.MockTransport(handler),
        base_url="https://vendor.test/",
    )
    return BaseApiClient(client=http, retort=Retort())


@pytest.fixture(autouse=True)
def _instant_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    # The backoff *delay* isn't under test here; skip the real sleep so the
    # retry tests stay instant.
    async def _no_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", _no_sleep)


async def test_retries_transient_read_timeout_then_succeeds() -> None:
    handler = _ScriptedHandler([_timeout(), _ok(7)])
    client = _client(handler)

    result = await client._get("orders", _Payload)

    assert result.value == 7
    assert handler.calls == 2


async def test_retries_server_error_then_succeeds() -> None:
    handler = _ScriptedHandler([_status(503), _ok(1)])
    client = _client(handler)

    result = await client._get("orders", _Payload)

    assert result.value == 1
    assert handler.calls == 2


async def test_does_not_retry_client_error() -> None:
    # A 404 is the caller's problem, not a transient one — retrying only delays
    # the inevitable. TCloudClient.get_order relies on the 404 surfacing so it
    # can turn it into a normal "order not found".
    handler = _ScriptedHandler([_status(404)])
    client = _client(handler)

    with pytest.raises(httpx2.HTTPStatusError):
        await client._get("orders/missing", _Payload)
    assert handler.calls == 1


async def test_gives_up_after_max_attempts() -> None:
    handler = _ScriptedHandler([_timeout()])
    client = _client(handler)

    with pytest.raises(httpx2.ReadTimeout):
        await client._get("orders", _Payload)
    assert handler.calls == MAX_ATTEMPTS


def _tcloud_client(handler: _ScriptedHandler) -> TCloudClient:
    http = httpx2.AsyncClient(
        transport=httpx2.MockTransport(handler),
        base_url="https://vendor.test/",
    )
    return TCloudClient(client=http, retort=Retort())


async def test_get_order_unwraps_data_envelope() -> None:
    # The single-order endpoint returns the order under a `data` key (like the
    # list endpoint, minus pagination), and the vendor sends far more fields
    # than the DTO declares — both must load without a NoRequiredFieldsLoadError.
    envelope = httpx2.Response(
        200,
        json={
            "data": {
                "id": "o1",
                "status": "done",
                "event": "e1",
                "created_at": "2026-08-14 11:43:06",
                "number": 118090379,
                "tickets": [
                    {
                        "id": "t1",
                        "serial": "YKT",
                        "number": 585594,
                        "barcode": "2724343490481812",
                        "status": "reserved",
                        "price": "500.00",
                        "nominal": "500.00",
                        "discount": "0.00",
                        "extra": "50.00",
                        "full": "550.00",
                        "set": "s1",
                        "tariff": None,
                    }
                ],
            }
        },
    )
    client = _tcloud_client(_ScriptedHandler([envelope]))

    order = await client.get_order("o1")

    assert order is not None
    assert order.id == "o1"
    assert order.status is OrderStatus.DONE
    assert [t.id for t in order.tickets] == ["t1"]


async def test_get_order_returns_none_on_not_found() -> None:
    client = _tcloud_client(_ScriptedHandler([_status(404)]))

    assert await client.get_order("missing") is None
