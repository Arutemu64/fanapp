from pydantic import BaseModel, SecretStr


class TCloudConfig(BaseModel):
    api_key: SecretStr
    # Secret path segment for the inbound webhook. TicketsCloud cannot sign or
    # authenticate its webhook calls, so we gate the endpoint with an
    # unguessable token embedded in the URL it POSTs to. When unset the webhook
    # fails closed (404).
    webhook_secret: SecretStr | None = None
