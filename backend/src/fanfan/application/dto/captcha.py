from typing import Any

from pydantic import BaseModel, Field


class CaptchaChallengeDTO(BaseModel):
    challenge: dict[str, Any] | None = Field(
        description="ALTCHA challenge, passed verbatim to the widget; its fields "
        "are the provider's, not part of this API. Null when captcha is disabled."
    )
