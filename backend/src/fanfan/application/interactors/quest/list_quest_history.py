from pydantic import BaseModel

from fanfan.application.dto.page import CursorPagination, cut_page
from fanfan.application.dto.quest import QuestHistoryItemDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.services.current_user import CurrentUserProvider


class ListQuestHistoryInput(BaseModel):
    pagination: CursorPagination


class ListQuestHistoryOutput(BaseModel):
    awards: list[QuestHistoryItemDTO]
    next_cursor: str | None


class ListQuestHistory:
    """A player's own awards, cancelled ones included, so the balance adds up."""

    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self, data: ListQuestHistoryInput) -> ListQuestHistoryOutput:
        current_user = await self.current_user_provider.require_user()
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        rows = await self.quest_award_gateway.read_awards_page(
            pagination=data.pagination, user_id=current_user.id
        )
        page, next_cursor = cut_page(rows, data.pagination)
        awards = [QuestHistoryItemDTO(**award.model_dump()) for award in page]
        return ListQuestHistoryOutput(awards=awards, next_cursor=next_cursor)
