import logging

from pydantic import BaseModel, Field

from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId, UserRole

logger = logging.getLogger(__name__)

MIN_AMOUNT = 1
MAX_AMOUNT = 100


class GenerateTicketsInput(BaseModel):
    role: UserRole
    amount: int = Field(ge=MIN_AMOUNT, le=MAX_AMOUNT)


class GenerateTicketsOutput(BaseModel):
    # One barcode per generated ticket, ready to be copied into a spreadsheet.
    barcodes: list[str]


class GenerateTickets:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        ticket_gateway: TicketGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ):
        self.current_user_provider = current_user_provider
        self.ticket_gateway = ticket_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: GenerateTicketsInput) -> GenerateTicketsOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.TICKETS_GENERATE
        )

        tickets = _build_tickets(
            role=data.role,
            amount=data.amount,
            issued_by_user_id=current_user.id,
        )
        await self.ticket_gateway.add_all(tickets)
        await self.uow.commit()

        logger.info(
            "Tickets generated",
            extra={
                "actor_id": str(current_user.id),
                "role": data.role.value,
                "amount": data.amount,
            },
        )
        return GenerateTicketsOutput(barcodes=[ticket.barcode for ticket in tickets])


def _build_tickets(
    *, role: UserRole, amount: int, issued_by_user_id: UserId
) -> list[Ticket]:
    # Deduplicate within the batch so a single request can never emit two
    # identical codes; cross-batch uniqueness is enforced by the DB constraint.
    tickets: list[Ticket] = []
    seen: set[str] = set()
    while len(tickets) < amount:
        ticket = Ticket.issue(role=role, issued_by_user_id=issued_by_user_id)
        if ticket.barcode in seen:
            continue
        seen.add(ticket.barcode)
        tickets.append(ticket)
    return tickets
