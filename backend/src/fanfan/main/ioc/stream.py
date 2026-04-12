from dishka import Provider, Scope, provide
from faststream.nats import NatsBroker
from nats.js import JetStreamContext

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.nats.config import NatsConfig
from fanfan.adapters.nats.events_broker import NatsEventBroker
from fanfan.adapters.nats.factory import NATSClient, create_nats_client
from fanfan.adapters.nats.realtime_gateway import NatsRealtimeGateway
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.presentation.faststream.broker import create_broker


class StreamProvider(Provider):
    scope = Scope.APP

    @provide
    def get_nats_config(self, config: EnvConfig) -> NatsConfig:
        return config.nats

    @provide
    async def get_broker(self, config: NatsConfig) -> NatsBroker:
        broker = create_broker(config=config)
        await broker.connect()
        return broker

    events_broker = provide(NatsEventBroker, provides=EventBroker)
    realtime_gateway = provide(NatsRealtimeGateway, provides=RealtimeGateway)

    @provide
    async def get_nats_client(self, config: NatsConfig) -> NATSClient:
        return await create_nats_client(config)

    @provide
    async def get_jetstream(self, nc: NATSClient) -> JetStreamContext:
        return nc.jetstream()
