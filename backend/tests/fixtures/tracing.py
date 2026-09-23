from collections.abc import Iterator

import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport


class _DropTransport(Transport):
    def capture_envelope(self, envelope: Envelope) -> None: ...


@pytest.fixture
def tracing() -> Iterator[None]:
    """A Sentry client with tracing on, sending nothing anywhere.

    Without one, get_traceparent() ignores the active span and returns the
    scope's fallback trace id, so trace propagation cannot be observed.
    """
    sentry_sdk.init(
        dsn="https://key@example.invalid/1",
        traces_sample_rate=1.0,
        transport=_DropTransport,
        default_integrations=False,
    )
    yield
    sentry_sdk.init()  # back to an inactive client for the rest of the suite
