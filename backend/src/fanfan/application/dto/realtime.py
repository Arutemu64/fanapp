from dataclasses import dataclass

SSE_CONNECTED_EVENT = "connected"


@dataclass(slots=True, frozen=True)
class SSEMessage:
    event_name: str
    data: dict | None = None
