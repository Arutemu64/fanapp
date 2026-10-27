from pydantic import BaseModel

from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.schedule_operations import ScheduleOperations
from fanfan.core.vo.schedule_entry import ScheduleEntryId


class MoveScheduleEventInput(BaseModel):
    event_id: ScheduleEntryId
    # None moves the event to the top of the schedule.
    place_after_entry_id: ScheduleEntryId | None


class MoveScheduleEvent:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        schedule_operations: ScheduleOperations,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.schedule_operations = schedule_operations

    async def __call__(self, data: MoveScheduleEventInput) -> None:
        user = await self.current_user_provider.require_user()
        await self.schedule_operations.move(
            user, data.event_id, data.place_after_entry_id
        )
