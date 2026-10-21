from dishka import AsyncContainer

from fanfan.application.dto.jobs import Job
from fanfan.application.interactors.notifications.delete_mailing_notifications import (
    DeleteMailingNotifications,
    DeleteMailingNotificationsInput,
)
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.presentation.worker.router import JobRouter

schedule_router = JobRouter()


@schedule_router.handler(ScheduleChangeCreated, name="process_schedule_change")
async def process_schedule_change(
    event: ScheduleChangeCreated, job: Job, container: AsyncContainer
) -> None:
    publish_schedule_updated = await container.get(PublishScheduleUpdated)
    interactor = await container.get(SendScheduleChangeNotifications)
    # Live update before the notification fan-out: the screen should not wait
    # on building a notification per subscriber, nor on a fan-out failure that
    # retries this job. A retry repeats the live update, which is harmless —
    # clients revalidate and get a 304 for a schedule they already hold.
    await publish_schedule_updated()
    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=event.schedule_change_id,
            occurred_at=job.created_at,
        )
    )


@schedule_router.handler(ScheduleChangeUndone, name="undo_schedule_change")
async def undo_schedule_change(
    event: ScheduleChangeUndone, _job: Job, container: AsyncContainer
) -> None:
    publish_schedule_updated = await container.get(PublishScheduleUpdated)
    # Cancel first: until it lands, notifications queued for the undone change
    # can still go out, so it must not wait on the cache warm-up or fail with
    # the live update. Idempotent, so a retry after a failed live update just
    # repeats it.
    if event.mailing_id:
        cancel = await container.get(DeleteMailingNotifications)
        await cancel(DeleteMailingNotificationsInput(mailing_id=event.mailing_id))
    await publish_schedule_updated()
