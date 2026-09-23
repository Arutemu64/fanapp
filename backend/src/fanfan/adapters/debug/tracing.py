import sentry_sdk

# The headers Sentry propagates a trace with; the names are Sentry's contract.
SENTRY_TRACE_HEADER = "sentry-trace"
BAGGAGE_HEADER = "baggage"


def current_trace_headers() -> dict[str, str]:
    """The active trace's propagation headers, or {} when no span is active.

    Only an active span counts: outside one (the scheduler, a CLI command) the
    scope still has a process-wide fallback trace id, and stamping that onto
    messages would stitch every unrelated message into one endless trace.
    """
    if sentry_sdk.get_current_span() is None:
        return {}
    headers: dict[str, str] = {}
    traceparent = sentry_sdk.get_traceparent()
    if traceparent:
        headers[SENTRY_TRACE_HEADER] = traceparent
    baggage = sentry_sdk.get_baggage()
    if baggage:
        headers[BAGGAGE_HEADER] = baggage
    return headers
