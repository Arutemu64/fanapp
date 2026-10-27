from pydantic import BaseModel, SecretStr


class FestEngineConfig(BaseModel):
    # Standard Webhooks secret (`whsec_<base64>`); unset disables the endpoint.
    webhook_secret: SecretStr | None = None
