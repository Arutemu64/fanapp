from pydantic import BaseModel, SecretStr


class VkConfig(BaseModel):
    client_id: str
    client_secret: SecretStr
