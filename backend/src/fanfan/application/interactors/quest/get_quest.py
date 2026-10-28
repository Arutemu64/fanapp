from pydantic import BaseModel

from fanfan.application.dto.quest import LeaderboardEntryDTO
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.quest_awards import QuestAwardGateway
from fanfan.application.services.current_user import CurrentUserProvider

LEADERBOARD_SIZE = 10


class GetQuestOutput(BaseModel):
    points: int
    rank: int | None
    leaderboard_entries: list[LeaderboardEntryDTO]
    own_entry: LeaderboardEntryDTO | None


class GetQuest:
    def __init__(
        self,
        settings_gateway: AppSettingsGateway,
        quest_award_gateway: QuestAwardGateway,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.settings_gateway = settings_gateway
        self.quest_award_gateway = quest_award_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> GetQuestOutput:
        current_user = await self.current_user_provider.require_user()
        settings = await self.settings_gateway.get()
        settings.ensure_quest_enabled()

        leaderboard, own = await self.quest_award_gateway.read_leaderboard(
            limit=LEADERBOARD_SIZE, user_id=current_user.id
        )
        if own is None:
            return GetQuestOutput(
                points=0, rank=None, leaderboard_entries=leaderboard, own_entry=None
            )

        own_entry = None
        if own.rank > LEADERBOARD_SIZE:
            own_entry = own
        return GetQuestOutput(
            points=own.player.points,
            rank=own.rank,
            leaderboard_entries=leaderboard,
            own_entry=own_entry,
        )
