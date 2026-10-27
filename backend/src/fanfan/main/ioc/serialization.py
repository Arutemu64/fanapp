from adaptix import Retort
from dishka import Provider, Scope, provide

from fanfan.adapters.serialization import create_retort


class SerializationProvider(Provider):
    scope = Scope.APP

    @provide
    def get_retort(self) -> Retort:
        return create_retort()
