import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.notifications import CancelMailingEvent
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)


class CancelMailingInput(BaseModel):
    mailing_id: MailingId


class CancelMailing:
    def __init__(
        self,
        mailing_repo: MailingRepository,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        trx: TransactionManager,
    ):
        self.mailing_repo = mailing_repo
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.events_broker = events_broker
        self.trx = trx

    async def __call__(self, data: CancelMailingInput) -> None:
        mailing = await self.mailing_repo.get(data.mailing_id)
        if mailing is None:
            raise MailingNotFound
        current_user = await self.current_user_provider.require_user()
        if (mailing.by_user_id != current_user.id) and (
            current_user.role is not UserRole.ORG
        ):
            raise AccessDenied(details={"reason": "MAILING_DELETE_FORBIDDEN"})
        mailing.set_as_cancelled()
        await self.mailing_repo.save(mailing)
        await self.trx.commit()
        await self.events_broker.publish(CancelMailingEvent(mailing_id=data.mailing_id))
        logger.info(
            "Mailing %s deleted by user %s",
            data.mailing_id,
            current_user.id,
        )
        return
