from pydantic import BaseModel, SecretStr

from fanfan.core.vo.user import UserRole


class TCloudConfig(BaseModel):
    api_key: SecretStr
    event_ids_map: dict[str, UserRole]
    # Secret path segment for the inbound webhook. TicketsCloud cannot sign or
    # authenticate its webhook calls, so we gate the endpoint with an
    # unguessable token embedded in the URL it POSTs to. When unset the webhook
    # fails closed (404).
    webhook_secret: SecretStr | None = None
