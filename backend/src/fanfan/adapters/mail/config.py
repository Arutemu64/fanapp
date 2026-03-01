from pydantic import BaseModel, SecretStr


class MailConfig(BaseModel):
    username: str
    password: SecretStr
    host: str
    port: int
