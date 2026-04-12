from pydantic import BaseModel


class PushSubscriptionDTO(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
