import time
from datetime import datetime
from typing import Any

import sentry_sdk
from procrastinate import JobContext
from procrastinate.middleware import AsyncCallNext
from procrastinate.worker import Worker
from sentry_sdk.tracing import Span, TransactionSource

from fanfan.core.exceptions.notifications import NotificationRetryAfter

# Sentry's queue instrumentation contract: these span ops and data keys are what
# its Queues view reads.
# https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/queues-module/
_PROCESS_OP = "queue.process"


async def sentry_middleware(
    call_next: AsyncCallNext,
    context: JobContext,
    worker: Worker,  # Procrastinate's worker middleware signature
) -> Any:  # noqa: ANN401  # whatever the task returns
    """Report job errors and continue the producer's Sentry trace.

    One request's work is one trace across the web app and every job it queued:
    the job carries the producer's trace headers (adapters/procrastinate).
    """
    job = context.job
    # One isolation scope per job: concurrent jobs share the worker's loop, and
    # tags or breadcrumbs from one must not leak into another.
    with sentry_sdk.isolation_scope():
        trace_headers = job.task_kwargs.get("trace_headers") or {}
        transaction = sentry_sdk.continue_trace(
            dict(trace_headers),
            op=_PROCESS_OP,
            name=job.task_name,
            source=TransactionSource.TASK,
        )
        with (
            sentry_sdk.start_transaction(transaction),
            sentry_sdk.start_span(op=_PROCESS_OP, name=job.task_name) as span,
        ):
            _describe_job(span, context)
            try:
                return await call_next()
            except NotificationRetryAfter:
                # Flood control, not a fault: the retry strategy waits it out.
                raise
            except Exception as error:
                # Reported here, inside the transaction, so the error links to
                # the trace that queued the job. Procrastinate's own ERROR log of
                # a job that gives up carries the same exception object, which
                # Sentry's dedupe drops.
                sentry_sdk.capture_exception(error)
                raise


def _describe_job(span: Span, context: JobContext) -> None:
    job = context.job
    span.set_data("messaging.message.id", str(job.id))
    span.set_data("messaging.destination.name", job.task_name)
    span.set_data("messaging.message.retry.count", job.attempts)
    occurred_at = job.task_kwargs.get("occurred_at")
    if isinstance(occurred_at, str):
        # Time from the producer's commit to this run, in ms.
        latency = time.time() - datetime.fromisoformat(occurred_at).timestamp()
        span.set_data("messaging.message.receive.latency", latency * 1000)
