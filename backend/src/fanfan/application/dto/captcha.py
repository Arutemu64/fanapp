from typing import Any

from pydantic import BaseModel, Field


class CaptchaChallengeDTO(BaseModel):
    # An untyped dict on purpose: the provider signs the exact JSON it issues,
    # so re-modelling it here would risk adding, dropping or renaming a field
    # and breaking the signature the client sends back. None = captcha disabled.
    challenge: dict[str, Any] | None = Field(
        description="ALTCHA challenge, passed verbatim to the widget; its fields "
        "are the provider's, not part of this API. Null when captcha is disabled."
    )
