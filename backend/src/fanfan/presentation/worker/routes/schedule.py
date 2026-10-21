from procrastinate import Blueprint

from fanfan.application.commands.notifications import CancelMailingCommand
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.schedule import (
    ScheduleChangeCreated,
    ScheduleChangeUndone,
)
from fanfan.presentation.worker.subscriber import Delivery, subscriber

schedule_tasks = Blueprint()


@subscriber(schedule_tasks, ScheduleChangeCreated, name="process_schedule_change")
async def process_schedule_change(
    event: ScheduleChangeCreated, delivery: Delivery
) -> None:
    publish_schedule_updated = await delivery.container.get(PublishScheduleUpdated)
    interactor = await delivery.container.get(SendScheduleChangeNotifications)
    # Live update before the notification fan-out: the screen should not wait
    # on building a notification per subscriber, nor on a fan-out failure that
    # retries this job. A retry repeats the live update, which is harmless —
    # clients revalidate and get a 304 for a schedule they already hold.
    await publish_schedule_updated()
    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=event.schedule_change_id,
            occurred_at=delivery.occurred_at,
        )
    )


@subscriber(schedule_tasks, ScheduleChangeUndone, name="undo_schedule_change")
async def undo_schedule_change(event: ScheduleChangeUndone, delivery: Delivery) -> None:
    # Cancel first: until it lands, notifications queued for the undone change
    # can still go out, so it must not wait on the cache warm-up or fail with
    # the live update.
    if event.mailing_id:
        uow = await delivery.container.get(UnitOfWork)
        uow.enqueue(CancelMailingCommand(mailing_id=event.mailing_id))
        await uow.commit()
    publish_schedule_updated = await delivery.container.get(PublishScheduleUpdated)
    await publish_schedule_updated()
