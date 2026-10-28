import logging
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field
from pydantic.types import UuidVersion
from pydantic_core import PydanticCustomError

from fanfan.application.commands.notifications import ProcessBroadcastCommand
from fanfan.application.dto.input import InputModel
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.notifications import MailingAlreadyExists
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.user import UserRole

logger = logging.getLogger(__name__)

BROADCAST_BODY_MAX_LENGTH = 500


def _within_utf16_limit(body: str) -> str:
    utf16_units = len(body.encode("utf-16-le")) // 2
    if utf16_units > BROADCAST_BODY_MAX_LENGTH:
        error_type = "string_too_long"
        message = "String should have at most {max_length} characters"
        context = {"max_length": BROADCAST_BODY_MAX_LENGTH}
        raise PydanticCustomError(error_type, message, context)
    return body


class SendBroadcastInput(InputModel):
    mailing_id: Annotated[
        MailingId,
        UuidVersion(7),
        Field(description="UUIDv7 the client generates once per broadcast form."),
    ]
    body: Annotated[
        str,
        Field(min_length=1, max_length=BROADCAST_BODY_MAX_LENGTH),
        AfterValidator(_within_utf16_limit),
    ]
    roles: list[UserRole] = Field(min_length=1)


class SendBroadcastOutput(BaseModel):
    mailing_id: MailingId


class SendBroadcast:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        user_gateway: UserGateway,
        mailing_gateway: MailingGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.user_gateway = user_gateway
        self.mailing_gateway = mailing_gateway
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SendBroadcastInput) -> SendBroadcastOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.NOTIFICATIONS_SEND
        )

        existing = await self.mailing_gateway.get(data.mailing_id)
        if existing is not None:
            if not existing.is_broadcast(
                by_user_id=current_user.id, body=data.body, roles=data.roles
            ):
                raise MailingAlreadyExists
            logger.info(
                "Broadcast replayed",
                extra={
                    "mailing_id": str(existing.id),
                    "actor_id": str(current_user.id),
                },
            )
            return SendBroadcastOutput(mailing_id=existing.id)

        mailing = Mailing.create(by_user_id=current_user.id, mailing_id=data.mailing_id)
        mailing.queue_broadcast(body=data.body, roles=data.roles)
        await self.mailing_gateway.add(mailing)
        self.uow.enqueue(
            ProcessBroadcastCommand(
                mailing_id=mailing.id, body=data.body, roles=data.roles
            )
        )
        await self.uow.commit()

        logger.info(
            "Broadcast initiated",
            extra={
                "mailing_id": str(mailing.id),
                "actor_id": str(current_user.id),
            },
        )
        return SendBroadcastOutput(mailing_id=mailing.id)
