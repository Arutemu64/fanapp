import logging
from typing import override

from cosplay2py import AsyncCosplay2
from cosplay2py.models import RequestStatus

from fanfan.application.ports.sources.cosplay import (
    CosplaySource,
    ExternalNomination,
    ExternalParticipant,
)

logger = logging.getLogger(__name__)


class Cosplay2Source(CosplaySource):
    """Anti-corruption layer over the Cosplay2 HTTP client.

    Translates vendor wire formats (topics, requests) into the neutral DTOs
    the application understands, and decides which vendor records the domain
    recognizes as participants.
    """

    def __init__(self, client: AsyncCosplay2) -> None:
        self.client = client

    @override
    async def fetch_nominations(self) -> list[ExternalNomination]:
        topics = await self.client.topics.get_list()
        return [
            ExternalNomination(
                external_id=topic.id,
                code=topic.card_code,
                title=topic.title,
            )
            for topic in topics
        ]

    @override
    async def fetch_participants(self) -> list[ExternalParticipant]:
        requests = await self.client.topics.get_all_requests()

        participants: list[ExternalParticipant] = []
        for request in requests:
            if request.status != RequestStatus.APPROVED or not request.voting_title:
                continue
            participants.append(
                ExternalParticipant(
                    external_id=request.id,
                    nomination_external_id=request.topic_id,
                    voting_number=request.voting_number,
                    voting_title=request.voting_title,
                )
            )
        return participants
