from dishka import Provider, Scope, provide

from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.sync_runs import SyncRunRecorderService
from fanfan.application.services.tickets import TicketService
from fanfan.application.services.tickets_import import TicketImportService
from fanfan.application.services.user import UserService
from fanfan.application.services.voting import VotingService


class ServicesProvider(Provider):
    scope = Scope.REQUEST

    tickets = provide(TicketService)
    voting = provide(VotingService)
    current_user = provide(CurrentUserProvider)
    perm = provide(PermissionService)
    user = provide(UserService)
    sync_run_recorder = provide(SyncRunRecorderService)

    # External
    ticket_import = provide(TicketImportService)
