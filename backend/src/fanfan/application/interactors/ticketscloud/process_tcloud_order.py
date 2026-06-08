from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.dto.order import Order
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.ticketscloud import TCloudService


class ProcessTCloudOrderInput(BaseModel):
    order: Order


class ProcessTCloudOrderOutput(BaseModel):
    new_tickets_count: int


class ProcessTCloudOrder:
    def __init__(self, tcloud_service: TCloudService, uow: UnitOfWork):
        self.tcloud_service = tcloud_service
        self.uow = uow

    async def __call__(self, data: ProcessTCloudOrderInput) -> ProcessTCloudOrderOutput:
        new_tickets_count = await self.tcloud_service.proceed_order(data.order)
        await self.uow.commit()
        return ProcessTCloudOrderOutput(new_tickets_count=new_tickets_count)
