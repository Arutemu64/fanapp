from __future__ import annotations

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
