from dataclasses import dataclass, field
from enum import StrEnum


class SSEEventName(StrEnum):
    """Canonical names for every Server-Sent Event the backend emits.

    This is the single source of truth on the backend side; the frontend
    mirrors it in `SSEEventMap` (frontend/src/lib/services/events.svelte.ts).
    The two must be kept in sync by hand — SSE events are not part of the
    OpenAPI spec, so there is no code generation between them.

    Naming standard (see docs/backend.md "Realtime (SSE)"):
      * snake_case, single token — NO dots. The NATS subject is built as
        `sse.broadcast.{event_name}` / `sse.user.{user_id}.{event_name}` and
        consumers subscribe with a single-token wildcard (`sse.broadcast.*`).
        A dot in the name would split into extra subject tokens and silently
        stop matching that wildcard.
      * Prefer `<entity>_<event>` for new names.
      * Every value here must have a matching key in the frontend `SSEEventMap`.
    """

    # Handshake sent once when a stream opens (see StreamEvents interactor).
    CONNECTION_ESTABLISHED = "connection_established"
    # Liveness heartbeat injected by the SSE route when the stream is idle.
    # Never published via RealtimeGateway — it exists so the frontend watchdog
    # can tell a quiet-but-healthy stream from a silently dead one.
    PING = "ping"
    # Schedule changed; clients should refetch the schedule.
    SCHEDULE_UPDATED = "schedule_updated"
    NOTIFICATION_CREATED = "notification_created"
    # A vendor sync run changed state; organizers should refetch sync sources.
    SYNC_RUN_UPDATED = "sync_run_updated"


@dataclass(slots=True, frozen=True)
class SSEMessage:
    event_name: SSEEventName
    # Default to an empty dict, not None, for payload-less signals (schedule_updated,
    # ping). Per the SSE spec, EventSource drops an event whose data buffer is empty
    # even when `event:` is set, so the named listener never fires; sending `{}` keeps
    # the data line non-empty. The router JSON-encodes the dict to `{}` on the wire.
    # https://html.spec.whatwg.org/multipage/server-sent-events.html#event-stream-interpretation
    data: dict = field(default_factory=dict)
