import logging

from pydantic import BaseModel, Field


class DebugConfig(BaseModel):
    # Defaults are production-safe (fail-closed): debug off, INFO logs, JSON on.
    # When ENV=dev these are relaxed to developer-friendly values unless a
    # DEBUG__* var is set explicitly. See EnvConfig._apply_environment_posture.
    #
    # `enabled` turns on FastAPI's debug mode (stack traces in HTTP responses)
    # and local uvicorn auto-reload — never enable it in production.
    enabled: bool = False
    test_mode: bool = False

    logging_level: int = logging.INFO
    json_logs: bool = True

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    sentry_profiles_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
