from dishka import Provider, Scope, provide

from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.mailing import MailingService
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.security import SecurityService
from fanfan.application.services.tickets import TicketService
from fanfan.application.services.ticketscloud import TCloudService
from fanfan.application.services.user import UserService
from fanfan.application.services.voting import VotingService
from fanfan.core.services.email_login import EmailService


class ServicesProvider(Provider):
    scope = Scope.REQUEST

    tickets = provide(TicketService)
    voting = provide(VotingService)
    security = provide(SecurityService)
    email = provide(EmailService)
    current_user = provide(CurrentUserProvider)
    notifications = provide(MailingService)
    perm = provide(PermissionService)
    user = provide(UserService)

    # External
    tcloud = provide(TCloudService)
