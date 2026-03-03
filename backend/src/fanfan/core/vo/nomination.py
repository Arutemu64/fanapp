from __future__ import annotations

from typing import NewType
from uuid import UUID

NominationId = NewType("NominationId", UUID)
NominationCode = NewType("NominationCode", str)
