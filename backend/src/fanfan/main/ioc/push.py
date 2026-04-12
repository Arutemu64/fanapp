from dishka import Provider, Scope, provide

from fanfan.adapters.push.push import PushNotifier


class PushProvider(Provider):
    scope = Scope.APP

    push_notifier = provide(PushNotifier, scope=scope.REQUEST)
