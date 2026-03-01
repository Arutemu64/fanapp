from dishka import Provider, Scope, provide

from fanfan.adapters.notifications.push import PushNotifier


class PushProvider(Provider):
    scope = Scope.APP

    push_notifier = provide(PushNotifier, scope=scope.REQUEST)
