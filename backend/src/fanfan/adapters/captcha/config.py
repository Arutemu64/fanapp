from pydantic import BaseModel, SecretStr


class AltchaConfig(BaseModel):
    # Signs every issued challenge, so a client cannot forge an easy one or
    # extend its expiry. Server-only: the frontend needs no key.
    hmac_key: SecretStr
