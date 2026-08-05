from pydantic import BaseModel, SecretStr


class VkConfig(BaseModel):
    client_id: str
    client_secret: SecretStr
    # Community (group) access token with the `messages` scope. Used only by the
    # VK community notifier to deliver messages; VK ID OAuth login uses the
    # client_id/client_secret pair above, not this token.
    community_token: SecretStr
