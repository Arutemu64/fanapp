from adaptix import Retort
from dishka import Provider, Scope, provide

from fanfan.adapters.serialization import create_retort


class SerializationProvider(Provider):
    scope = Scope.APP

    # Single shared base Retort for adapters that (de)serialize plain
    # dataclass models. Specialized retorts (e.g. RedisRetort) keep their own
    # bindings so DI can resolve them by their distinct NewType.
    @provide
    def get_retort(self) -> Retort:
        return create_retort()
