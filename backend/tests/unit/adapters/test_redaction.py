import logging

from sentry_sdk.types import Event

from fanfan.adapters.debug.logging import SecretPathFilter
from fanfan.adapters.debug.redaction import redact_secret_paths
from fanfan.adapters.debug.telemetry import _scrub_sensitive_data

TOKEN = "s3cr3t-token"
WEBHOOK_URL = f"https://fan.test/api/webhooks/tcloud/{TOKEN}"


def test_redacts_the_ticketscloud_webhook_token() -> None:
    assert (
        redact_secret_paths(f"/api/webhooks/tcloud/{TOKEN}?x=1")
        == "/api/webhooks/tcloud/[Filtered]?x=1"
    )


def test_leaves_other_paths_alone() -> None:
    assert redact_secret_paths("/api/webhooks/festengine") == "/api/webhooks/festengine"


def test_access_log_line_hides_the_token() -> None:
    # The argument layout uvicorn's access logger uses.
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:1", "POST", f"/api/webhooks/tcloud/{TOKEN}", "1.1", 200),
        exc_info=None,
    )

    assert SecretPathFilter().filter(record)
    assert TOKEN not in record.getMessage()


def test_sentry_event_url_hides_the_token() -> None:
    event: Event = {"request": {"url": WEBHOOK_URL}}

    scrubbed = _scrub_sensitive_data(event)

    assert scrubbed["request"]["url"] == (
        "https://fan.test/api/webhooks/tcloud/[Filtered]"
    )
