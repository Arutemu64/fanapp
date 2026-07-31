from pydantic import BaseModel, Field

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)


class GetScheduleOutput(BaseModel):
    schedule: list[ScheduleEventFullDTO]
    # Shipped with the schedule rather than left on GET /settings, which is
    # gated behind SETTINGS_MANAGE: with it, plus each event's duration and the
    # current event's actual_start_time, a viewer has everything needed to work
    # out the wait themselves and keep it live between fetches (ADR-0013).
    transition_buffer_seconds: int = Field(
        description="Setup time assumed between consecutive events, in seconds.",
    )


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
        return GetScheduleOutput(
            schedule=events,
            transition_buffer_seconds=settings.limits.transition_buffer_seconds,
        )
