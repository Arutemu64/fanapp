from datetime import UTC, datetime

from pydantic import BaseModel

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.services.schedule_timing import apply_expected_start_times


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEventFullDTO]


class GetSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        settings_gateway: AppSettingsGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.settings_gateway = settings_gateway

    async def __call__(self) -> GetScheduleOutput:
        # The schedule is universal — identical for every viewer — so it carries
        # no per-user data and can be cached once on the client. Subscriptions
        # are served separately by GetSubscriptions.
        events = await self.schedule_gateway.read_list_schedule()
        settings = await self.settings_gateway.get()
        events = apply_expected_start_times(
            events,
            transition_buffer=settings.limits.transition_buffer,
            now=datetime.now(UTC),
        )
        return GetScheduleOutput(schedule=events)
