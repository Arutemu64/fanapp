from dishka import Provider, Scope, provide

from fanfan.adapters.push.push import PushNotifier
from fanfan.application.ports.notifier import PushNotifierPort


class PushProvider(Provider):
    scope = Scope.APP

    push_notifier = provide(
        PushNotifier, scope=Scope.REQUEST, provides=PushNotifierPort
    )
