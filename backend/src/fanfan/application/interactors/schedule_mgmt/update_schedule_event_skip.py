from pydantic import BaseModel

from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.schedule_operations import ScheduleOperations
from fanfan.core.vo.schedule_entry import ScheduleEntryId


class UpdateScheduleEventSkipInput(BaseModel):
    event_id: ScheduleEntryId
    is_skipped: bool


class UpdateScheduleEventSkip:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        schedule_operations: ScheduleOperations,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.schedule_operations = schedule_operations

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
        user = await self.current_user_provider.require_user()
        await self.schedule_operations.set_skipped(
            user, data.event_id, is_skipped=data.is_skipped
        )
