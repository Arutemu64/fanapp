from dishka import Provider, Scope, provide_all

from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.sync_run_tracker import SyncRunTracker
from fanfan.application.services.tickets import TicketService
from fanfan.application.services.tickets_import import TicketImportService
from fanfan.application.services.user import UserService
from fanfan.application.services.voting import VotingService


class ServicesProvider(Provider):
    scope = Scope.REQUEST

    services = provide_all(
        TicketService,
        VotingService,
        CurrentUserProvider,
        PermissionService,
        UserService,
        TicketImportService,
        SyncRunTracker,
    )
