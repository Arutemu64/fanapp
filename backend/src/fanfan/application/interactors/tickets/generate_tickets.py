import logging
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic.types import UuidVersion

from fanfan.application.dto.input import InputModel
from fanfan.application.ports.gateways.tickets import TicketGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.tickets import TicketBatchAlreadyExists
from fanfan.core.models.ticket_batch import TicketBatch
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.ticket import TicketBatchId
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)

MIN_AMOUNT = 1
MAX_AMOUNT = 100


class GenerateTicketsInput(InputModel):
    batch_id: Annotated[
        TicketBatchId,
        UuidVersion(7),
        Field(description="UUIDv7 the client generates once per generate form."),
    ]
    role: UserRole
    amount: int = Field(ge=MIN_AMOUNT, le=MAX_AMOUNT)


class GenerateTicketsOutput(BaseModel):
    barcodes: list[str]


class GenerateTickets:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        ticket_gateway: TicketGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.ticket_gateway = ticket_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: GenerateTicketsInput) -> GenerateTicketsOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.TICKETS_MANAGE
        )

        existing = await self.ticket_gateway.get_batch(data.batch_id)
        if existing is not None:
            if not existing.is_same_request(
                by_user_id=current_user.id, role=data.role, amount=data.amount
            ):
                raise TicketBatchAlreadyExists
            logger.info(
                "Ticket batch replayed",
                extra={
                    "batch_id": str(existing.id),
                    "actor_id": str(current_user.id),
                },
            )
            return GenerateTicketsOutput(barcodes=existing.barcodes)

        batch = TicketBatch.issue(
            batch_id=data.batch_id,
            role=data.role,
            amount=data.amount,
            issued_by_user_id=current_user.id,
        )
        await self.ticket_gateway.add_batch(batch)
        await self.uow.commit()

        logger.info(
            "Tickets generated",
            extra={
                "batch_id": str(batch.id),
                "actor_id": str(current_user.id),
                "role": data.role.value,
                "amount": data.amount,
            },
        )
        return GenerateTicketsOutput(barcodes=batch.barcodes)
