from pydantic import BaseModel, EmailStr

from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import EmailAlreadyExists
from fanfan.core.utils.email import normalize_email


class ChangeEmailInput(BaseModel):
    new_email: EmailStr


class ChangeEmail:
    def __init__(
        self,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ):
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: ChangeEmailInput) -> None:
        normalized_new_email = normalize_email(data.new_email)
        current_user = await self.current_user_provider.require_user()

        if (
            current_user.email == normalized_new_email
            or current_user.pending_email == normalized_new_email
        ):
            return

        existing_user = await self.user_repo.get_by_any_email(normalized_new_email)
        if existing_user is not None and existing_user.id != current_user.id:
            raise EmailAlreadyExists

        # Keep the active email unchanged until the new address proves
        # mailbox ownership through the confirmation code flow. The recorded
        # EmailConfirmationCodeRequested event is dispatched by the UnitOfWork
        # on commit (current_user was registered when loaded).
        current_user.request_email_change(normalized_new_email)
        await self.user_repo.save(current_user)
        await self.uow.commit()
