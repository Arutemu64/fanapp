from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Ticket:
    id: str
    barcode: str | None
