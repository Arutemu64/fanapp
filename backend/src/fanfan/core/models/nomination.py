from dataclasses import dataclass

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.nomination import NominationId


@dataclass(slots=True, kw_only=True)
class Nomination(AggregateRoot):
    id: NominationId
    cosplay2_id: int
    code: str
    title: str
    is_votable: bool
    # Optional external URL where users can preview the nominated works.
    works_url: str | None = None
