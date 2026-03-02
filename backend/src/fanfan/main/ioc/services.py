from dishka import Provider, Scope, provide

from fanfan.core.services.cosplay2 import Cosplay2Service
from fanfan.core.services.notifications import NotificationService
from fanfan.core.services.perm import PermService
from fanfan.core.services.security import SecurityService
from fanfan.core.services.tickets import TicketService
from fanfan.core.services.ticketscloud import TCloudService
from fanfan.core.services.voting import VotingService


class ServicesProvider(Provider):
    scope = Scope.REQUEST

    tickets = provide(TicketService)
    voting = provide(VotingService)
    security = provide(SecurityService)
    notifications = provide(NotificationService)
    perm = provide(PermService)

    # External
    tcloud = provide(TCloudService)
    cosplay2 = provide(Cosplay2Service)
