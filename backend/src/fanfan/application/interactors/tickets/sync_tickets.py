import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.sources.tickets import (
    RevokedExternalTicket,
    TicketsSource,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.tickets_import import TicketImportService

logger = logging.getLogger(__name__)

COMMIT_BATCH_SIZE = 200


class SyncTicketsOutput(BaseModel):
    new_tickets_count: int
    revoked_tickets_count: int


class SyncTickets:
    def __init__(
        self,
        source: TicketsSource,
        app_settings_gateway: AppSettingsGateway,
        ticket_import_service: TicketImportService,
        uow: UnitOfWork,
    ) -> None:
        self.source = source
        self.app_settings_gateway = app_settings_gateway
        self.ticket_import_service = ticket_import_service
        self.uow = uow

    async def __call__(self) -> SyncTicketsOutput:
        tickets_config = (await self.app_settings_gateway.get()).tickets

        refunded = {revoked async for revoked in self.source.fetch_revoked_tickets()}

        new_tickets_count = 0
        revoked_tickets_count = 0
        seen_since_commit = 0
        async for external in self.source.fetch_all_tickets():
            sale = RevokedExternalTicket(
                order_id=external.order_id, external_id=external.external_id
            )
            is_refunded = sale in refunded
            imported = await self.ticket_import_service.import_ticket(
                external,
                role=tickets_config.role_for_tcloud_event(external.event_id),
                refunded=is_refunded,
            )
            if imported and is_refunded:
                revoked_tickets_count += 1
            elif imported:
                new_tickets_count += 1
            seen_since_commit += 1
            if seen_since_commit >= COMMIT_BATCH_SIZE:
                await self.uow.commit()
                seen_since_commit = 0
                logger.info(
                    "TicketsCloud sync progress",
                    extra={"new_tickets": new_tickets_count},
                )
        await self.uow.commit()

        for revoked in refunded:
            if await self.ticket_import_service.revoke_ticket(revoked):
                revoked_tickets_count += 1
        await self.uow.commit()

        return SyncTicketsOutput(
            new_tickets_count=new_tickets_count,
            revoked_tickets_count=revoked_tickets_count,
        )
