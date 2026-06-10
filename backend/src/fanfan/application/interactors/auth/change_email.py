from pydantic import BaseModel, EmailStr

from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.vo.email import Email


class ChangeEmailInput(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: ChangeEmailInput) -> None:
        new_email = Email(data.new_email)
        current_user = await self.current_user_provider.require_user()

        if new_email in (current_user.email, current_user.pending_email):
            return

        existing_user = await self.user_gateway.get_by_any_email(new_email.value)
        if existing_user is not None and existing_user.id != current_user.id:
            raise EmailAlreadyExists

        # Keep the active email unchanged until the new address proves
        # mailbox ownership through the confirmation code flow. The recorded
        # EmailConfirmationCodeRequested event is dispatched by the UnitOfWork
        # on commit (current_user was registered when loaded).
        current_user.request_email_change(new_email)
        await self.user_gateway.save(current_user)
        await self.uow.commit()
