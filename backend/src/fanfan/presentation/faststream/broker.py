from faststream.nats import NatsBroker

from fanfan.adapters.nats.config import MAX_RECONNECT_ATTEMPTS, NatsConfig
from fanfan.presentation.faststream.logger import get_stream_logger
from fanfan.presentation.faststream.middleware import SentryMiddleware
from fanfan.presentation.faststream.redelivery import RedeliveryMiddleware

# How long stop() waits for in-flight handlers before closing (FastStream's own
# default, spelled out). The faststream service's stop_grace_period in
# docker-compose.yml must stay above it, or Docker kills the wait short.
# https://faststream.ag2.ai/0.7/getting-started/lifespan/lifecycle/
_GRACEFUL_TIMEOUT_SECONDS = 15.0


def create_broker(
    config: NatsConfig,
    *,
    name: str,
) -> NatsBroker:
    return NatsBroker(
        config.build_connection_str(),
        name=name,
        max_reconnect_attempts=MAX_RECONNECT_ATTEMPTS,
        graceful_timeout=_GRACEFUL_TIMEOUT_SECONDS,
        logger=get_stream_logger(),
        middlewares=[SentryMiddleware, RedeliveryMiddleware],
    )
