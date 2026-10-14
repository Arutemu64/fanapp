from dataclasses import dataclass


# Only the fields the sync reads. adaptix requires every declared field and
# skips unknown keys, so each extra field here is one more way for a single
# vendor payload to fail a whole sweep.
@dataclass(slots=True, frozen=True)
class Ticket:
    id: str
    # Assigned only once the order is done.
    barcode: str | None
