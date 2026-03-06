from pydantic import BaseModel, HttpUrl, SecretStr


class WebConfig(BaseModel):
    host: str
    port: int

    base_url: HttpUrl
    path: str = "/"
    secret_key: SecretStr
    jwt_issuer: str = "fanapp-api"
    jwt_audience: str = "fanapp-web"
