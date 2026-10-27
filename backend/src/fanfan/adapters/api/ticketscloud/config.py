from pydantic import BaseModel, SecretStr


class TCloudConfig(BaseModel):
    api_key: SecretStr
    webhook_secret: SecretStr | None = None
