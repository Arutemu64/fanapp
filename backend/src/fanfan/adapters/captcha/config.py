from pydantic import BaseModel, SecretStr


class AltchaConfig(BaseModel):
    hmac_key: SecretStr
