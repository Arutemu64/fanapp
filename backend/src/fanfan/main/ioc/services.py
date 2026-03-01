from dishka import Provider, Scope, provide

from fanfan.core.services.auth import AuthService
from fanfan.core.services.cosplay2 import Cosplay2Service
from fanfan.core.services.mailing import MailingService
from fanfan.core.services.notifications import NotificationService
from fanfan.core.services.permissions import UserPermissionService
from fanfan.core.services.schedule import ScheduleService
from fanfan.core.services.tickets import TicketService
from fanfan.core.services.ticketscloud import TCloudService
from fanfan.core.services.voting import VotingService


class ServicesProvider(Provider):
    scope = Scope.REQUEST

    mailing = provide(MailingService)
    schedule = provide(ScheduleService)
    tickets = provide(TicketService)
    voting = provide(VotingService)
    user_perms = provide(UserPermissionService)
    auth = provide(AuthService)
    notifications = provide(NotificationService)

    # External
    tcloud = provide(TCloudService)
    cosplay2 = provide(Cosplay2Service)
