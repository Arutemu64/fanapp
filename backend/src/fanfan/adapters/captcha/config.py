from pydantic import BaseModel, SecretStr


class TurnstileConfig(BaseModel):
    # Server-side secret key from the Cloudflare Turnstile dashboard.
    # The matching site key lives on the frontend (PUBLIC_TURNSTILE_SITE_KEY).
    secret_key: SecretStr
