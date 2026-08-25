from adaptix import Retort
from dishka import Provider, Scope, provide

from fanfan.adapters.serialization import create_retort


class SerializationProvider(Provider):
    scope = Scope.APP

    # Single shared base Retort for adapters that (de)serialize plain
    # dataclass models. A specialized retort with different bindings would be
    # provided under its own NewType so DI can resolve it separately.
    @provide
    def get_retort(self) -> Retort:
        return create_retort()
