import logging

from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.ticketscloud import TCloudService

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 200


class SyncTCloudOutput(BaseModel):
    new_tickets_count: int
    removed_tickets_count: int


class SyncTCloud:
    def __init__(
        self,
        client: TCloudClient,
        tcloud_service: TCloudService,
        uow: UnitOfWork,
    ):
        self.client = client
        self.tcloud_service = tcloud_service
        self.uow = uow

    async def __call__(self) -> SyncTCloudOutput:
        new_tickets_count, removed_tickets_count = 0, 0
        orders_init = await self.client.get_orders(page=1, page_size=DEFAULT_PAGE_SIZE)
        logger.info(
            "TicketsCloud sync started",
            extra={"order_count": orders_init.total_count},
        )
        # Orders. Reuse the page we already fetched above and request the rest
        # starting from page 2, so page 1 is not fetched twice.
        for page in range(1, orders_init.pagination.total + 1):
            if page == 1:
                result = orders_init
            else:
                result = await self.client.get_orders(
                    page=page, page_size=DEFAULT_PAGE_SIZE
                )
            for order_data in result.data:
                new_tickets_count += await self.tcloud_service.proceed_order(order_data)
            await self.uow.commit()
            logger.info(
                "TicketsCloud sync progress",
                extra={
                    "new_tickets": new_tickets_count,
                    "removed_tickets": removed_tickets_count,
                },
            )
        # TODO Find a way to correctly proceed refunds
        return SyncTCloudOutput(
            new_tickets_count=new_tickets_count,
            removed_tickets_count=removed_tickets_count,
        )
