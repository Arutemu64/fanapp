from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestConfigDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    max_award: int = Field(ge=1)
    cancel_window_minutes: int = Field(ge=0)


class AppSettingsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Voting time range is managed separately, under voting:manage — see the
    # voting dashboard (GET/PATCH /voting/dashboard) — and the announcement
    # cooldown and changeover under schedule:setup (GET/PUT /schedule/settings).
    # They are deliberately not here.
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
    # Shows or hides the quest card and tool; the quest endpoints enforce it too.
    quest_enabled: bool
    # Lets the volunteer's award form validate before sending; volunteers cannot
    # read the organizer settings.
    quest_max_award: int
    # Added per act to the wait estimate the schedule shows, the same one the
    # subscription reminder fires on (ADR-0043).
    schedule_changeover_seconds: int
