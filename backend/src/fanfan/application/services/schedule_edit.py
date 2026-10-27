import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.schedule import ScheduleEditTooFast
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserId


@dataclass(frozen=True, slots=True, kw_only=True)
class AnnouncedChangeContext:
    """What the service knows only after the mutation, for building the change."""

    mailing_id: MailingId
    user_id: UserId
    next_event_changed: bool


type ChangeFactory = Callable[[AnnouncedChangeContext], ScheduleChange]


class ScheduleEditService:
    """Runs one schedule edit transaction: authorize, lock, mutate, commit.

    Every interactor that writes schedule events goes through here, so the
    rules that must hold for all of them live in one place: the edit lock and the
    announcement cooldown ordering.
    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        settings_gateway: AppSettingsGateway,
        schedule_gateway: ScheduleEntryGateway,
        changes_gateway: ScheduleChangeGateway,
        mailing_gateway: MailingGateway,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.settings_gateway = settings_gateway
        self.schedule_gateway = schedule_gateway
        self.changes_gateway = changes_gateway
        self.mailing_gateway = mailing_gateway
        self.uow = uow

    async def announce(
        self,
        permission: Permission,
        mutate: Callable[[User], Awaitable[ChangeFactory]],
        *,
        already_applied: Callable[[], Awaitable[bool]],
    ) -> User:
        """Edit the schedule and announce it to subscribers.

        ``mutate`` applies the domain change and returns a factory for the
        ``ScheduleChange`` that records it. Returns the acting user.

        ``already_applied`` reports whether the schedule is already in the
        requested state. If so, the edit is a no-op: nothing is written or
        announced. A retry after a lost response, or a second operator making
        the same call, therefore succeeds without telling everyone twice
        (docs/adr/0034). It runs under the edit lock, so no concurrent edit can
        change the answer, and before the cooldown, so a no-op is never a 429.
        """
        user = await self._authorize(permission)
        settings = await self.settings_gateway.get()
        await self.schedule_gateway.lock_for_edit()
        if await already_applied():
            return user
        await self._ensure_announcement_cooldown(settings.limits.announcement_timeout)

        next_event_before = await self.schedule_gateway.get_next()
        build_change = await mutate(user)
        next_event_after = await self.schedule_gateway.get_next()

        mailing = Mailing.create(by_user_id=user.id)
        await self.mailing_gateway.add(mailing)
        change = build_change(
            AnnouncedChangeContext(
                mailing_id=mailing.id,
                user_id=user.id,
                next_event_changed=next_event_before != next_event_after,
            )
        )
        await self.changes_gateway.add(change)

        await self.uow.commit()
        return user

    async def edit(
        self,
        permission: Permission,
        mutate: Callable[[User], Awaitable[None]],
    ) -> User:
        """Edit the schedule without an announcement or cooldown (undo, import).

        Returns the acting user.
        """
        user = await self._authorize(permission)
        await self.schedule_gateway.lock_for_edit()
        await mutate(user)
        await self.uow.commit()
        return user

    async def _authorize(self, permission: Permission) -> User:
        user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(user=user, permission=permission)
        return user

    async def _ensure_announcement_cooldown(self, cooldown_seconds: int) -> None:
        """Reject an announced edit that comes too soon after the previous one.

        Must run after ``ScheduleEntryGateway.lock_for_edit``: under that lock no
        other edit can record a change between this check and the commit, so the
        cooldown commits together with the edit and a failed edit never spends it.
        Every announced edit records a ScheduleChange, which is what makes the
        newest one the last announcement. Undo deletes its change, so an undone
        edit stops counting — its announcement was withdrawn with it.
        """
        elapsed = await self.changes_gateway.read_seconds_since_last_change()
        if elapsed is None or elapsed >= cooldown_seconds:
            return
        raise ScheduleEditTooFast(retry_after=math.ceil(cooldown_seconds - elapsed))
