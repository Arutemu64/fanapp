import logging

from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.ticketscloud import TCloudService

logger = logging.getLogger(__name__)


class ProcessTCloudOrderInput(BaseModel):
    order_id: str


class ProcessTCloudOrderOutput(BaseModel):
    new_tickets_count: int


class ProcessTCloudOrder:
    def __init__(
        self,
        client: TCloudClient,
        tcloud_service: TCloudService,
        uow: UnitOfWork,
    ):
        self.client = client
        self.tcloud_service = tcloud_service
        self.uow = uow

    async def __call__(self, data: ProcessTCloudOrderInput) -> ProcessTCloudOrderOutput:
        # The webhook body is untrusted: TicketsCloud cannot sign its requests,
        # so we only take the order id from it and fetch the authoritative order
        # from the authenticated API. A leaked webhook token alone therefore
        # cannot mint tickets from a forged payload.
        order = await self.client.get_order(data.order_id)
        if order is None:
            logger.warning(
                "TicketsCloud order not found, ignoring",
                extra={"order_id": data.order_id},
            )
            return ProcessTCloudOrderOutput(new_tickets_count=0)

        new_tickets_count = await self.tcloud_service.proceed_order(order)
        await self.uow.commit()
        logger.info(
            "TicketsCloud order processed",
            extra={"order_id": data.order_id, "new_tickets": new_tickets_count},
        )
        return ProcessTCloudOrderOutput(new_tickets_count=new_tickets_count)
