from faststream.nats import NatsBroker

from fanfan.adapters.nats.config import NatsConfig
from fanfan.presentation.faststream.logger import get_stream_logger
from fanfan.presentation.faststream.middleware import SentryMiddleware


def create_broker(
    config: NatsConfig,
) -> NatsBroker:
    return NatsBroker(
        config.build_connection_str(),
        logger=get_stream_logger(),
        middlewares=[SentryMiddleware],
    )
