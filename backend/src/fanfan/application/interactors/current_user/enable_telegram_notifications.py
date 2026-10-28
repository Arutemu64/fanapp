import logging

from fanfan.application.interactors.current_user.enable_vk_notifications import (
    NOTIFICATIONS_CHECK_COOLDOWN_SECONDS,
)
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.notifier import TelegramNotifierPort
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.notifications import (
    NotificationRetryAfter,
    NotificationsCheckTooFast,
    TelegramBotBlocked,
    UserNotReachable,
)
from fanfan.core.exceptions.rate_limit import CooldownActive
from fanfan.core.exceptions.users import SocialAccountNotLinked
from fanfan.core.models.notification import Notification
from fanfan.core.vo.notification import NotificationType, generate_notification_id
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


def _confirmation(user_id: UserId) -> Notification:
    """Sent straight to the bot, never stored: it only proves the bot gets through."""
    return Notification(
        id=generate_notification_id(),
        user_id=user_id,
        title="Уведомления включены",
        body="Сюда будут приходить уведомления ФАН ФАН.",
        type=NotificationType.TEST,
        path="/profile/notifications",
        mailing_id=None,
        seen_at=None,
    )


class EnableTelegramNotifications:
    """Turn Telegram notifications on once a confirmation message gets through.

    Telegram has no way to ask whether a bot may write without writing, so the
    check is a real message the user asked for.
    """

    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        social_identity_gateway: SocialIdentityGateway,
        user_gateway: UserGateway,
        tg_notifier: TelegramNotifierPort,
        cooldown: Cooldown,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.social_identity_gateway = social_identity_gateway
        self.user_gateway = user_gateway
        self.tg_notifier = tg_notifier
        self.cooldown = cooldown
        self.uow = uow

    async def __call__(self) -> None:
        user = await self.current_user_provider.require_user()
        identity = await self.social_identity_gateway.get_by_provider(
            user_id=user.id, provider=SocialProvider.TELEGRAM
        )
        if identity is None:
            raise SocialAccountNotLinked

        claim = self.cooldown.claim(
            f"telegram_messages_check:{user.id}", NOTIFICATIONS_CHECK_COOLDOWN_SECONDS
        )
        try:
            async with claim:
                await self.tg_notifier.send_notification(_confirmation(user.id))
        except CooldownActive as e:
            raise NotificationsCheckTooFast(retry_after=e.details["retry_after"]) from e
        except NotificationRetryAfter as e:
            raise NotificationsCheckTooFast(retry_after=e.retry_after) from e
        except UserNotReachable as e:
            raise TelegramBotBlocked from e

        user.update_settings(receive_telegram_notifications=True)
        await self.user_gateway.save(user)
        await self.uow.commit()
        logger.info(
            "Telegram notifications switched on", extra={"user_id": str(user.id)}
        )
