from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.dto.quest import QuestAwardItemDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.quest_award import cancel_refusal
from fanfan.core.vo.permission import Permission


class ListQuestAwardsInput(BaseModel):
    pagination: CursorPagination


class ListQuestAwardsOutput(BaseModel):
    awards: list[QuestAwardItemDTO]
    next_cursor: str | None


class ListQuestAwards:
    """The awards a volunteer gave, so they can spot and undo a slip.

    Holders of quest:manage see every volunteer's awards: they settle disputes.
    """

    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self, data: ListQuestAwardsInput) -> ListQuestAwardsOutput:
        current_user = await self.current_user_provider.require_user()
        can_manage = await self.perm_service.has(current_user, Permission.QUEST_MANAGE)
        if not can_manage:
            await self.perm_service.ensure(
                user=current_user, permission=Permission.QUEST_AWARD
            )
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        awarded_by = None
        if not can_manage:
            awarded_by = current_user.id
        rows = await self.quest_award_gateway.read_awards_page(
            pagination=data.pagination, awarded_by=awarded_by
        )
        page, next_cursor = cut_page(rows, data.pagination)

        cancel_window = timedelta(minutes=settings.quest.cancel_window_minutes)
        now = datetime.now(UTC)
        awards: list[QuestAwardItemDTO] = []
        for award in page:
            awarded_by_id = None
            if award.awarded_by is not None:
                awarded_by_id = award.awarded_by.id
            refusal = cancel_refusal(
                awarded_by=awarded_by_id,
                created_at=award.created_at,
                cancelled_at=award.cancelled_at,
                by_user_id=current_user.id,
                can_manage=can_manage,
                cancel_window=cancel_window,
                now=now,
            )
            awards.append(
                QuestAwardItemDTO(**award.model_dump(), can_cancel=refusal is None)
            )
        return ListQuestAwardsOutput(awards=awards, next_cursor=next_cursor)
