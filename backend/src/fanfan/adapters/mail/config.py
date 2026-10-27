from pydantic import BaseModel, NameEmail, SecretStr


class MailConfig(BaseModel):
    username: str
    password: SecretStr
    host: str
    port: int

    sender: NameEmail

    timeout: int = 10
