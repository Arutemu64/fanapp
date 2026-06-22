import logging
from collections import defaultdict

from fanfan.adapters.api.cosplay2.client import Cosplay2Client
from fanfan.adapters.api.cosplay2.dto.requests import RequestStatus, RequestValueDTO
from fanfan.application.ports.sources.cosplay import (
    CosplaySource,
    ExternalNomination,
    ExternalParticipant,
)
from fanfan.core.models.participant import ParticipantValue

logger = logging.getLogger(__name__)


class Cosplay2Source(CosplaySource):
    """Anti-corruption layer over the Cosplay2 HTTP client.

    Translates vendor wire formats (topics, requests, request values) into the
    neutral DTOs the application understands, and decides which vendor records
    the domain recognizes as participants.
    """

    def __init__(self, client: Cosplay2Client):
        self.client = client

    async def fetch_nominations(self) -> list[ExternalNomination]:
        topics = await self.client.get_topics_list()
        return [
            ExternalNomination(
                external_id=topic.id,
                code=topic.card_code,
                title=topic.title,
            )
            for topic in topics
        ]

    async def fetch_participants(self) -> list[ExternalParticipant]:
        requests = await self.client.get_all_requests()
        values = await self.client.get_all_values()

        # Group values by request id once, so each request lookup is O(1)
        # instead of rescanning the full values list per request.
        values_by_request: dict[int, list[RequestValueDTO]] = defaultdict(list)
        for value in values:
            values_by_request[value.request_id].append(value)

        participants: list[ExternalParticipant] = []
        for request in requests:
            # Only approved requests that still carry a voting title can be
            # represented as participants; everything else is not a participant
            # the domain recognizes, so it is dropped at the boundary.
            if request.status != RequestStatus.APPROVED or not request.voting_title:
                continue
            participants.append(
                ExternalParticipant(
                    external_id=request.id,
                    nomination_external_id=request.topic_id,
                    voting_number=request.voting_number,
                    voting_title=request.voting_title,
                    values=[
                        ParticipantValue(title=v.title, type=v.type, value=v.value)
                        for v in values_by_request.get(request.id, [])
                    ],
                )
            )
        return participants
