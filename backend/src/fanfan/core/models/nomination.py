from dataclasses import dataclass

from fanfan.core.exceptions.votes import VotingDisabled
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.nomination import NominationId


@dataclass(slots=True, kw_only=True)
class Nomination(AggregateRoot):
    id: NominationId
    cosplay2_id: int
    code: str
    title: str
    is_votable: bool
    works_url: str | None = None

    def ensure_votable(self) -> None:
        if not self.is_votable:
            raise VotingDisabled
