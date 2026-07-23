from pydantic import BaseModel, SecretStr


class SmartCaptchaConfig(BaseModel):
    # Server-side key from the Yandex SmartCaptcha console.
    # The matching client key lives on the frontend (PUBLIC_SMARTCAPTCHA_CLIENT_KEY).
    server_key: SecretStr
