from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest
from cosplay2py import AsyncCosplay2
from pydantic import SecretStr

from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.cosplay2.source import Cosplay2Source
from fanfan.main.ioc.cosplay2 import Cosplay2Provider

pytestmark = pytest.mark.unit

type VendorPayloads = tuple[Cosplay2Source, dict[str, Any]]


@pytest.fixture
async def vendor_payloads() -> AsyncIterator[VendorPayloads]:
    payloads: dict[str, Any] = {}

    def respond(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["X-API-Key"] == "test-key"
        assert request.headers["X-API-Secret"] == "test-secret"
        return httpx2.Response(200, json=payloads[request.url.path])

    async with (
        httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as http,
        AsyncCosplay2(
            subdomain="test-event",
            api_key="test-key",
            api_secret="test-secret",
            http_client=http,
        ) as client,
    ):
        yield Cosplay2Source(client), payloads


def _request(
    request_id: int,
    *,
    status: str = "approved",
    voting_title: str | None = "Title",
    topic_id: int = 1,
    voting_number: int | None = 1,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "topic_id": topic_id,
        "number": request_id,
        "user_id": 100,
        "voting_number": voting_number,
        "voting_title": voting_title,
        "status": status,
    }


async def test_fetch_nominations_maps_topics(vendor_payloads: VendorPayloads) -> None:
    source, payloads = vendor_payloads
    payloads["/api/topics/get_list"] = [
        {
            "id": 1,
            "event_id": 2,
            "url_code": "solo",
            "card_code": "A1",
            "title": "Best Costume",
            "order": 1,
            "voting_group": 0,
            "voting_public": 1,
            "voting_jury": 0,
            "print_badges": 0,
            "card_enabled": 1,
            "default_duration": 1.5,
            "public_requests": "NO",
        }
    ]

    nominations = await source.fetch_nominations()

    assert len(nominations) == 1
    assert nominations[0].external_id == 1
    assert nominations[0].code == "A1"
    assert nominations[0].title == "Best Costume"


async def test_fetch_participants_keeps_only_approved_with_voting_title(
    vendor_payloads: VendorPayloads,
) -> None:
    source, payloads = vendor_payloads
    payloads["/api/topics/get_all_requests"] = [
        _request(1),
        *[
            _request(i, status=status)
            for i, status in enumerate(
                ["pending", "waiting", "materials", "review", "disapproved"],
                start=2,
            )
        ],
        _request(7, voting_title=None),
        _request(8, voting_title=""),
    ]

    participants = await source.fetch_participants()

    assert [p.external_id for p in participants] == [1]


@pytest.mark.parametrize("voting_number", [1, None])
async def test_fetch_participants_maps_request_fields(
    vendor_payloads: VendorPayloads, voting_number: int | None
) -> None:
    source, payloads = vendor_payloads
    payloads["/api/topics/get_all_requests"] = [
        _request(42, topic_id=7, voting_number=voting_number),
    ]

    participants = await source.fetch_participants()

    assert len(participants) == 1
    participant = participants[0]
    assert participant.external_id == 42
    assert participant.nomination_external_id == 7
    assert participant.voting_title == "Title"
    assert participant.voting_number == voting_number


@pytest.mark.parametrize("endpoint", ["get_list", "get_all_requests"])
async def test_empty_vendor_response_returns_empty_list(
    vendor_payloads: VendorPayloads, endpoint: str
) -> None:
    source, payloads = vendor_payloads
    payloads[f"/api/topics/{endpoint}"] = []

    result = (
        await source.fetch_nominations()
        if endpoint == "get_list"
        else await source.fetch_participants()
    )

    assert result == []


async def test_provider_configures_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pools: list[httpx2.AsyncClient] = []

    async def send(
        http: httpx2.AsyncClient, request: httpx2.Request, *, follow_redirects: bool
    ) -> httpx2.Response:
        pools.append(http)
        assert (
            str(request.url)
            == "https://configured.cosplay2.ru/api/topics/get_all_requests"
        )
        assert request.headers["X-API-Key"] == "configured-key"
        assert request.headers["X-API-Secret"] == "configured-secret"
        assert request.extensions["timeout"]["connect"] == 10.0
        assert request.extensions["timeout"]["read"] == 30.0
        assert not follow_redirects
        return httpx2.Response(200, json=[], request=request)

    monkeypatch.setattr(httpx2.AsyncClient, "send", send)
    config = Cosplay2Config(
        event_id=1,
        subdomain="configured",
        api_key="configured-key",
        api_secret=SecretStr("configured-secret"),
    )
    clients = Cosplay2Provider().get_cosplay2_client(config)
    async for client in clients:
        assert await Cosplay2Source(client).fetch_participants() == []
        assert not pools[0].is_closed
    assert pools[0].is_closed
