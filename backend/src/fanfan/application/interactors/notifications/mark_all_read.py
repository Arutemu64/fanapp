from datetime import UTC, datetime

from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider


class MarkAllRead:
    def __init__(
        self,
        notifications_repo: NotificationGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.notifications_repo = notifications_repo
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self) -> None:
        current_user_id = await self.current_user_provider.require_user_id()
        # seen_at is a timestamptz column, so the stored instant is identical
        # regardless of tzinfo; use UTC to match every other interactor.
        timestamp = datetime.now(UTC)
        await self.notifications_repo.mark_all_read_for_user(
            user_id=current_user_id,
            timestamp=timestamp,
        )
        await self.uow.commit()
