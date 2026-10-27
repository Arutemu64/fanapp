from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SSEEventName(StrEnum):
    """Canonical names for every Server-Sent Event the backend emits.

    Published in the OpenAPI spec as the `GET /events` item's `event` type, so
    the generated `SseEventName` union checks the frontend's `SSEEventMap`.

    Naming standard (see docs/backend.md "Realtime (SSE)"):
      * snake_case, single token — NO dots. The NATS subject is built as
        `sse.broadcast.{event_name}` / `sse.user.{user_id}.{event_name}` and
        consumers subscribe with a single-token wildcard (`sse.broadcast.*`).
        A dot in the name would split into extra subject tokens and silently
        stop matching that wildcard.
      * Prefer `<entity>_<event>` for new names.
    """

    CONNECTION_ESTABLISHED = "connection_established"
    PING = "ping"
    SCHEDULE_UPDATED = "schedule_updated"
    NOTIFICATION_CREATED = "notification_created"
    SYNC_RUN_UPDATED = "sync_run_updated"
    CONFIG_UPDATED = "config_updated"


@dataclass(slots=True, frozen=True)
class SSEMessage:
    event_name: SSEEventName
    data: dict[str, Any] = field(default_factory=dict)
