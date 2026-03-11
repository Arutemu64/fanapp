from pydantic import BaseModel, SecretStr


class TelegramConfig(BaseModel):
    token: SecretStr
    client_id: str
    client_secret: SecretStr
