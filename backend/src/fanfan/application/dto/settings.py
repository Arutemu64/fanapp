from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestConfigDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    max_award: int = Field(ge=1)
    cancel_window_minutes: int = Field(ge=0)


class AppSettingsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    festival_start: datetime
    festival_end: datetime
    quest: QuestConfigDTO


class PublicConfigDTO(BaseModel):
    """Public, unauthenticated projection of AppSettings served at GET /config.

    Deliberately omits `limits` (ADR-0008 projection tuning is organizer-only).
    Carries the raw `festival_start` and `festival_end` so the client can run the
    live countdown and pick its before/during/after phase itself — flipping at
    each boundary without provoking a 403 on a guarded endpoint. Voting
    availability is intentionally not here: the UI reads it per-user from
    GET /voting/status (which already reflects the time range as a DISABLED
    state), so a second public copy would only be a redundant source of truth to
    drift.
    """

    model_config = ConfigDict(from_attributes=True)

    festival_start: datetime
    festival_end: datetime
    quest_enabled: bool
    quest_max_award: int
    schedule_changeover_seconds: int
