from typing import NewType

import nats
from nats.aio.client import Client

from fanfan.adapters.nats.config import MAX_RECONNECT_ATTEMPTS, NatsConfig

NATSClient = NewType("NATSClient", Client)


async def create_nats_client(config: NatsConfig, *, name: str) -> NATSClient:
    return NATSClient(
        await nats.connect(
            config.build_connection_str(),
            name=name,
            max_reconnect_attempts=MAX_RECONNECT_ATTEMPTS,
        )
    )
