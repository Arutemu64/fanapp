from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.constraints import get_constraint_name
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.users import EmailVerificationRequestedEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import EmailAlreadyExists, UserNotFound
from fanfan.core.utils.email import normalize_email


class ChangeEmailCommand(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        event_broker: EventBroker,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ):
        self.event_broker = event_broker
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: ChangeEmailCommand) -> None:
        async with self.uow:
            normalized_new_email = normalize_email(data.new_email)
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound

            if (
                current_user.email == normalized_new_email
                or current_user.pending_email == normalized_new_email
            ):
                return

            existing_user = await self.user_gateway.get_user_by_any_email(
                normalized_new_email
            )
            if existing_user is not None and existing_user.id != current_user.id:
                raise EmailAlreadyExists

            try:
                # Keep the active email unchanged until the new address proves
                # mailbox ownership through the verification flow.
                current_user.pending_email = normalized_new_email
                await self.user_gateway.save_user(current_user)
                await self.uow.commit()
            except IntegrityError as e:
                constraint_name = get_constraint_name(e)
                if constraint_name in {"ix_users_email", "ix_users_pending_email"}:
                    raise EmailAlreadyExists from e
                raise
            await self.event_broker.publish(
                EmailVerificationRequestedEvent(user_id=current_user.id)
            )
