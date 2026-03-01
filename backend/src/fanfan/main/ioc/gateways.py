from dishka import Provider, Scope, provide

from fanfan.adapters.db.gateways.app_settings import (
    SettingsGateway,
)
from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.adapters.db.gateways.nominations import NominationGateway
from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.adapters.db.gateways.participants import (
    ParticipantGateway,
)
from fanfan.adapters.db.gateways.permissions import PermissionGateway
from fanfan.adapters.db.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.subscriptions import (
    SubscriptionGateway,
)
from fanfan.adapters.db.gateways.tickets import TicketGateway
from fanfan.adapters.db.gateways.user_flags import UserFlagGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.gateways.votes import VoteGateway


class GatewaysProvider(Provider):
    scope = Scope.REQUEST

    nominations = provide(NominationGateway)
    participants = provide(ParticipantGateway)
    schedule_events = provide(ScheduleEventGateway)
    schedule_changes = provide(ScheduleChangeGateway)
    settings = provide(SettingsGateway)
    subscriptions = provide(SubscriptionGateway)
    tickets = provide(TicketGateway)
    users = provide(UserGateway)
    votes = provide(VoteGateway)
    flags = provide(UserFlagGateway)
    permissions = provide(PermissionGateway)
    push_subscriptions = provide(PushSubscriptionGateway)
    mailings = provide(MailingGateway)
    notifications = provide(NotificationGateway)
