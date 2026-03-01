from pydantic import BaseModel

from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.schedule import ScheduleEventFullDTO


class GetScheduleResult(BaseModel):
    schedule: list[ScheduleEventFullDTO]


class GetSchedule:
    def __init__(
        self, schedule_gateway: ScheduleEventGateway, id_provider: IdProvider
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.id_provider = id_provider

    async def __call__(self) -> GetScheduleResult:
        current_user_id = await self.id_provider.get_current_user_id()
        events = await self.schedule_gateway.read_list_schedule(user_id=current_user_id)
        return GetScheduleResult(schedule=events)
