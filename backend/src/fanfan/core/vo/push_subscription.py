from typing import NewType
from uuid import UUID, uuid7

PushSubscriptionId = NewType("PushSubscriptionId", UUID)


def generate_push_subscription_id() -> PushSubscriptionId:
    return PushSubscriptionId(uuid7())
