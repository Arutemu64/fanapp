from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LimitsConfigDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Keep the validation rule close to the schema so OpenAPI documents it too.
    announcement_timeout: int = Field(ge=1)
    transition_buffer: int = Field(ge=0)


class AppSettingsDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voting_enabled: bool
    festival_start: datetime
    festival_ended: bool
    limits: LimitsConfigDTO


class PublicConfigDTO(BaseModel):
    """Public, unauthenticated projection of AppSettings served at GET /config.

    Deliberately omits `limits` (ADR-0008 projection tuning is organizer-only).
    Carries the raw `festival_start` so the client can run the live countdown,
    plus `festival_ended` so the UI can pick its phase without provoking a 403 on
    a guarded endpoint. Voting availability is intentionally not here: the UI
    reads it per-user from GET /voting/status (which already reflects the
    `voting_enabled` flag as a DISABLED state), so a second public copy would only
    be a redundant source of truth to drift.
    """

    model_config = ConfigDict(from_attributes=True)

    festival_start: datetime
    festival_ended: bool
