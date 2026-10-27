from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class ExternalNomination:
    external_id: int
    code: str
    title: str


@dataclass(slots=True, frozen=True)
class ExternalParticipant:
    external_id: int
    nomination_external_id: int
    voting_number: int | None
    voting_title: str


class CosplaySource(Protocol):
    """Read port into the external cosplay competition platform (Cosplay2).

    Returns neutral application DTOs already filtered to the records the domain
    recognizes; vendor wire formats never cross this boundary.
    """

    async def fetch_nominations(self) -> list[ExternalNomination]: ...
    async def fetch_participants(self) -> list[ExternalParticipant]: ...
