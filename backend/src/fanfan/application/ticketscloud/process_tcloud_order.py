from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.dto.order import Order
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.services.ticketscloud import TCloudService


class ProcessTCloudOrderDTO(BaseModel):
    order: Order


class ProcessTCloudOrderResult(BaseModel):
    new_tickets_count: int


class ProcessTCloudOrder:
    def __init__(self, tcloud_service: TCloudService, uow: UnitOfWork):
        self.tcloud_service = tcloud_service
        self.uow = uow

    async def __call__(self, data: ProcessTCloudOrderDTO) -> ProcessTCloudOrderResult:
        async with self.uow:
            new_tickets_count = await self.tcloud_service.proceed_order(data.order)
            await self.uow.commit()
            return ProcessTCloudOrderResult(new_tickets_count=new_tickets_count)
