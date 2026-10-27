import logging
from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic.types import UuidVersion

from fanfan.application.commands.notifications import CreateNotificationCommand
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.quest import QuestAwardAlreadyExists
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.quest_award import QuestAward
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.quest import QuestAwardId
from fanfan.core.vo.user import USER_NUMBER_MAX, USER_NUMBER_MIN, UserNumber

logger = logging.getLogger(__name__)


class AwardQuestPointsInput(BaseModel):
    award_id: Annotated[
        QuestAwardId,
        UuidVersion(7),
        Field(description="UUIDv7 the client generates once per award form."),
    ]
    user_number: Annotated[UserNumber, Field(ge=USER_NUMBER_MIN, le=USER_NUMBER_MAX)]
    amount: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=200)


class AwardQuestPointsOutput(BaseModel):
    award_id: QuestAwardId


class AwardQuestPoints:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: AwardQuestPointsInput) -> AwardQuestPointsOutput:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.QUEST_AWARD
        )
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        message = data.message.strip()
        player = await self.user_gateway.get_by_number(data.user_number)
        if player is None:
            raise UserNotFound

        existing = await self.quest_award_gateway.get(data.award_id)
        if existing is not None:
            if not existing.is_same_award(
                user_id=player.id,
                amount=data.amount,
                message=message,
                awarded_by=current_user.id,
            ):
                raise QuestAwardAlreadyExists
            logger.info(
                "Quest award replayed",
                extra={
                    "award_id": str(existing.id),
                    "actor_id": str(current_user.id),
                },
            )
            return AwardQuestPointsOutput(award_id=existing.id)

        award = QuestAward.create(
            award_id=data.award_id,
            user_id=player.id,
            amount=data.amount,
            message=message,
            awarded_by=current_user.id,
            max_amount=settings.quest.max_award,
            now=datetime.now(UTC),
        )
        await self.quest_award_gateway.add(award)
        self.uow.enqueue(
            CreateNotificationCommand(notification=award.award_notification())
        )
        await self.uow.commit()

        logger.info(
            "Quest points awarded",
            extra={
                "award_id": str(award.id),
                "actor_id": str(current_user.id),
                "target_user_id": str(player.id),
                "amount": award.amount,
            },
        )
        return AwardQuestPointsOutput(award_id=award.id)
