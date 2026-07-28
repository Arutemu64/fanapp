import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.csrf import ensure_trusted_origin

pytestmark = pytest.mark.unit

TRUSTED_ORIGIN = "https://fanfan.example"


@pytest.fixture
def config() -> WebConfig:
    return WebConfig(
        host="0.0.0.0",  # noqa: S104 — bind address, not a trust decision
        port=8000,
        public_url=f"{TRUSTED_ORIGIN}/",
        secret_key=SecretStr("test-secret"),
    )


def build_request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/login/telegram",
            "headers": [
                (name.encode("latin-1"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
        }
    )


@pytest.mark.parametrize(
    "headers",
    [
        # The form submit our own login page makes.
        {"sec-fetch-site": "same-origin", "origin": TRUSTED_ORIGIN},
        # User-initiated (address bar, bookmark) — no other site can forge this.
        {"sec-fetch-site": "none"},
        # Browser without Fetch Metadata: the Origin fallback carries the check.
        {"origin": TRUSTED_ORIGIN},
    ],
)
def test_accepts_requests_the_app_itself_initiated(
    config: WebConfig, headers: dict[str, str]
) -> None:
    ensure_trusted_origin(build_request(headers), config)


@pytest.mark.parametrize(
    "headers",
    [
        # A form on an attacker's page. Note the trusted Origin is ignored:
        # Fetch Metadata wins when present, so a spoofed Origin cannot rescue it.
        {"sec-fetch-site": "cross-site", "origin": TRUSTED_ORIGIN},
        {"sec-fetch-site": "same-site"},
        {"origin": "https://attacker.example"},
        # Neither header — not a browser whose initiator we can establish.
        {},
    ],
)
def test_rejects_everything_else(config: WebConfig, headers: dict[str, str]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        ensure_trusted_origin(build_request(headers), config)

    assert exc_info.value.status_code == 403
