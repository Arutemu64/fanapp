from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid7

from fanfan.core.vo.nomination import NominationId


@dataclass(slots=True, kw_only=True)
class Nomination:
    id: NominationId = field(default_factory=uuid7)
    cosplay2_id: int
    code: str
    title: str
    is_votable: bool
