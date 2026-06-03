from dataclasses import dataclass, field

from fanfan.core.events.base import AppEvent


@dataclass(slots=True)
class AggregateRoot:
    _events: list[AppEvent] = field(
        default_factory=list, init=False, compare=False, repr=False
    )

    def record_event(self, event: AppEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[AppEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
