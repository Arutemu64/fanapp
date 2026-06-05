from typing import NewType
from uuid import UUID, uuid7

SubscriptionId = NewType("SubscriptionId", UUID)


def generate_subscription_id() -> SubscriptionId:
    return SubscriptionId(uuid7())
