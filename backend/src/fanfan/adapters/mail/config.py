from pydantic import BaseModel, NameEmail, SecretStr


class MailConfig(BaseModel):
    username: str
    password: SecretStr
    host: str
    port: int

    sender: NameEmail

    # SMTP socket timeout in seconds. Codes are sent synchronously on the
    # request path, so a hung server would otherwise block the caller for
    # aiosmtplib's 60s default; 10s fails fast within a user's patience while
    # leaving ample headroom for a healthy send.
    timeout: int = 10
