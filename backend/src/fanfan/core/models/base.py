from dataclasses import dataclass, field

from fanfan.core.events.base import DomainEvent


@dataclass(slots=True)
class AggregateRoot:
    _events: list[DomainEvent] = field(
        default_factory=list, init=False, compare=False, repr=False
    )

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
