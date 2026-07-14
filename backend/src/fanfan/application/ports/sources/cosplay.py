from dataclasses import dataclass
from typing import Protocol


# external_id is the port's neutral vocabulary for "the id in the source system".
# The adapter maps the vendor id onto it; the interactor maps it onto the domain
# model's existing `cosplay2_id` field. Domain/DB names stay vendor-specific.
@dataclass(slots=True, frozen=True)
class ExternalNomination:
    external_id: int
    code: str
    title: str


@dataclass(slots=True, frozen=True)
class ExternalParticipant:
    external_id: int  # source request id
    nomination_external_id: int  # matches an ExternalNomination.external_id
    voting_number: int | None
    voting_title: str  # guaranteed present; the source filters out the None case


class CosplaySource(Protocol):
    """Read port into the external cosplay competition platform (Cosplay2).

    Returns neutral application DTOs already filtered to the records the domain
    recognizes; vendor wire formats never cross this boundary.
    """

    async def fetch_nominations(self) -> list[ExternalNomination]: ...
    async def fetch_participants(self) -> list[ExternalParticipant]: ...
