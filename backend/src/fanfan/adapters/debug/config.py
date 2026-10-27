import logging

from pydantic import BaseModel, Field


class DebugConfig(BaseModel):
    enabled: bool = False
    test_mode: bool = False

    logging_level: int = logging.INFO
    json_logs: bool = True

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    sentry_profiles_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
