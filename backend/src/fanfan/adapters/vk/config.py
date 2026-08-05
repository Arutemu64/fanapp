from pydantic import BaseModel, SecretStr


class VkConfig(BaseModel):
    client_id: str
    client_secret: SecretStr
    # Group (community) access token with the `messages` scope. Bound to a
    # single group, so it identifies the sender — messages.send needs no group
    # id. Used only by the VK notifier; VK ID OAuth login uses the
    # client_id/client_secret pair above, not this token.
    group_token: SecretStr
