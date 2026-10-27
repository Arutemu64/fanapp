import logging

from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.services.schedule_edit import (
    AnnouncedChangeContext,
    ChangeFactory,
    ScheduleEditService,
)
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import ScheduleEntryId

logger = logging.getLogger(__name__)


class ScheduleOperations:
    """The announced stage edits, run as a given user.

    Organizers reach them through their interactors, FestEngine through its
    webhook, so both share the lock, cooldown, change record and mailing.
    Each returns whether the schedule changed.
    """

    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def set_current(self, actor: User, event_id: ScheduleEntryId | None) -> bool:
        async def already_applied() -> bool:
            current_event = await self.schedule_gateway.get_current()
            if current_event is None:
                return event_id is None
            return current_event.id == event_id

        async def mutate() -> ChangeFactory:
            previous_current_event = await self.schedule_gateway.get_current()
            if previous_current_event:
                previous_current_event.unset_current()
                await self.schedule_gateway.save(previous_current_event)

            if event_id is not None:
                event = await self.schedule_gateway.get_event(event_id)
                if event is None:
                    raise EventNotFound
                event.set_current()
                await self.schedule_gateway.save(event)
            else:
                event = None

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                return ScheduleChange.set_as_current(
                    changed_event_id=event.id if event else None,
                    previous_event_id=previous_current_event.id
                    if previous_current_event
                    else None,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                )

            return build_change

        changed = await self.schedule_edit.announce(
            actor,
            Permission.SCHEDULE_MANAGE,
            mutate,
            already_applied=already_applied,
        )
        logger.info(
            "Schedule event set as current",
            extra={
                "event_id": str(event_id) if event_id else None,
                "actor_id": str(actor.id),
                "changed": changed,
            },
        )
        return changed

    async def move(
        self,
        actor: User,
        event_id: ScheduleEntryId,
        place_after_entry_id: ScheduleEntryId | None,
    ) -> bool:
        """Move the event after an entry, or to the very start for ``None``."""

        async def already_applied() -> bool:
            event = await self.schedule_gateway.get_event(event_id)
            if event is None:
                return False
            previous_entry = await self.schedule_gateway.get_previous_by_order(
                event.order
            )
            if previous_entry is None:
                return place_after_entry_id is None
            return previous_entry.id == place_after_entry_id

        async def mutate() -> ChangeFactory:
            event = await self.schedule_gateway.get_event(event_id)
            if event is None:
                raise EventNotFound
            previous_entry = await self.schedule_gateway.get_previous_by_order(
                event.order
            )

            await self._place(event, place_after_entry_id)
            await self.schedule_gateway.save(event)

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                return ScheduleChange.moved(
                    event_id=event.id,
                    previous_entry_id=previous_entry.id if previous_entry else None,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                    next_event_changed=ctx.next_event_changed,
                )

            return build_change

        changed = await self.schedule_edit.announce(
            actor,
            Permission.SCHEDULE_MANAGE,
            mutate,
            already_applied=already_applied,
        )
        logger.info(
            "Schedule event moved",
            extra={
                "event_id": str(event_id),
                "place_after_entry_id": str(place_after_entry_id)
                if place_after_entry_id
                else None,
                "actor_id": str(actor.id),
                "changed": changed,
            },
        )
        return changed

    async def _place(
        self, event: ScheduleEvent, place_after_entry_id: ScheduleEntryId | None
    ) -> None:
        if place_after_entry_id is None:
            first_entry = await self.schedule_gateway.get_first()
            event.place_before_first(first_entry)
            return
        place_after_entry = await self.schedule_gateway.get_entry(place_after_entry_id)
        if place_after_entry is None:
            raise EventNotFound
        place_before_entry = await self.schedule_gateway.get_next_by_order(
            place_after_entry.order
        )
        event.place_after(place_after_entry, place_before_entry)

    async def set_skipped(
        self, actor: User, event_id: ScheduleEntryId, *, is_skipped: bool
    ) -> bool:
        async def already_applied() -> bool:
            event = await self.schedule_gateway.get_event(event_id)
            return event is not None and event.is_skipped == is_skipped

        async def mutate() -> ChangeFactory:
            event = await self.schedule_gateway.get_event(event_id)
            if event is None:
                raise EventNotFound

            if is_skipped:
                event.skip()
            else:
                event.unskip()
            await self.schedule_gateway.save(event)

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                factory = (
                    ScheduleChange.skipped
                    if event.is_skipped
                    else ScheduleChange.unskipped
                )
                return factory(
                    event_id=event.id,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                    next_event_changed=ctx.next_event_changed,
                )

            return build_change

        changed = await self.schedule_edit.announce(
            actor,
            Permission.SCHEDULE_MANAGE,
            mutate,
            already_applied=already_applied,
        )
        logger.info(
            "Schedule event skip updated",
            extra={
                "event_id": str(event_id),
                "is_skipped": is_skipped,
                "actor_id": str(actor.id),
                "changed": changed,
            },
        )
        return changed
