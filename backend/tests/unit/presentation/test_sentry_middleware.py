import time
from typing import Any, cast

import pytest
import sentry_sdk
from procrastinate import App, JobContext, PsycopgConnector
from procrastinate.jobs import Job

from fanfan.adapters.debug.tracing import current_trace_headers
from fanfan.presentation.worker.middleware import sentry_middleware

pytestmark = pytest.mark.unit

_TRACE_ID = "771a43a4192642f0b136d5159a501700"
_PARENT = f"{_TRACE_ID}-b0e6f15b45c36b12-1"


def _context(trace_headers: dict[str, str] | None) -> JobContext:
    job = Job(
        id=1,
        queue="default",
        lock=None,
        queueing_lock=None,
        task_name="probe",
        task_kwargs={"message": {}, "trace_headers": trace_headers},
    )
    return JobContext(
        app=App(connector=PsycopgConnector()),
        job=job,
        start_timestamp=time.time(),
        abort_reason=lambda: None,
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_job_continues_the_producer_trace() -> None:
    seen: list[str] = []

    async def run() -> None:
        seen.append(sentry_sdk.get_traceparent() or "")

    # The middleware never reads the worker.
    await sentry_middleware(run, _context({"sentry-trace": _PARENT}), cast("Any", None))

    [traceparent] = seen
    assert traceparent.startswith(_TRACE_ID)


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_job_without_trace_headers_starts_its_own_trace() -> None:
    seen: list[str] = []

    async def run() -> None:
        seen.append(sentry_sdk.get_traceparent() or "")

    await sentry_middleware(run, _context(None), cast("Any", None))

    [traceparent] = seen
    assert not traceparent.startswith(_TRACE_ID)


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_job_error_propagates_to_the_worker() -> None:
    # Procrastinate decides on a retry from the exception, so the middleware
    # must report it without swallowing it.
    async def run() -> None:
        msg = "boom"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        await sentry_middleware(run, _context(None), cast("Any", None))


@pytest.mark.usefixtures("tracing")
def test_no_trace_headers_outside_a_span() -> None:
    # Outside a span the scope still has a fallback trace id; stamping it would
    # join every job the scheduler queues into one endless trace.
    assert current_trace_headers() == {}
