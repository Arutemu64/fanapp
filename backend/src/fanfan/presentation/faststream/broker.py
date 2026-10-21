from faststream.nats import NatsBroker

from fanfan.adapters.nats.config import MAX_RECONNECT_ATTEMPTS, NatsConfig
from fanfan.presentation.faststream.logger import get_stream_logger
from fanfan.presentation.faststream.middleware import SentryMiddleware
from fanfan.presentation.faststream.redelivery import RedeliveryMiddleware


def create_broker(
    config: NatsConfig,
    *,
    name: str,
) -> NatsBroker:
    return NatsBroker(
        config.build_connection_str(),
        name=name,
        max_reconnect_attempts=MAX_RECONNECT_ATTEMPTS,
        logger=get_stream_logger(),
        middlewares=[SentryMiddleware, RedeliveryMiddleware],
    )
