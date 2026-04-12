from pydantic import BaseModel, EmailStr

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.events.users import EmailVerificationRequestedEvent
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.utils.email import normalize_email


class ChangeEmailInput(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        event_broker: EventBroker,
        user_repo: UserRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
    ):
        self.event_broker = event_broker
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: ChangeEmailInput) -> None:
        normalized_new_email = normalize_email(data.new_email)
        current_user = await get_current_user(
            id_provider=self.id_provider, user_repo=self.user_repo
        )

        if (
            current_user.email == normalized_new_email
            or current_user.pending_email == normalized_new_email
        ):
            return

        existing_user = await self.user_repo.get_by_any_email(normalized_new_email)
        if existing_user is not None and existing_user.id != current_user.id:
            raise EmailAlreadyExists

        # Keep the active email unchanged until the new address proves
        # mailbox ownership through the verification flow.
        current_user.pending_email = normalized_new_email
        await self.user_repo.save(current_user)
        await self.trx.commit()

        await self.event_broker.publish(
            EmailVerificationRequestedEvent(user_id=current_user.id)
        )
