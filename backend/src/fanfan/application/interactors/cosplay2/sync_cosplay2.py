import contextlib
import logging
from dataclasses import replace

from fanfan.adapters.api.cosplay2.client import Cosplay2Client
from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.cosplay2.dto.requests import (
    Request,
    RequestStatus,
    RequestValueDTO,
)
from fanfan.adapters.api.cosplay2.dto.topics import Topic
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.participants import (
    NonApprovedRequest,
    RequestHasNoVotingTitle,
)
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant, ParticipantValue
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id

logger = logging.getLogger(__name__)


class SyncCosplay2:
    def __init__(
        self,
        client: Cosplay2Client,
        config: Cosplay2Config,
        uow: UnitOfWork,
        nomination_gateway: NominationGateway,
        participant_gateway: ParticipantGateway,
    ):
        self.participant_gateway = participant_gateway
        self.nomination_gateway = nomination_gateway
        self.client = client
        self.config = config
        self.uow = uow

    async def _process_topic(self, topic: Topic) -> Nomination:
        nomination = await self.nomination_gateway.get_by_cosplay2_id(topic.id)

        # Update or create nomination
        if nomination:
            nomination = replace(nomination, code=topic.card_code, title=topic.title)
            await self.nomination_gateway.save(nomination)
            logger.info("Nomination %s updated", nomination.cosplay2_id)
        else:
            nomination = Nomination(
                id=generate_nomination_id(),
                cosplay2_id=topic.id,
                code=topic.card_code,
                title=topic.title,
                is_votable=False,
            )
            await self.nomination_gateway.add(nomination)
            logger.info("Nomination %s added", nomination.id)

        return nomination

    async def _process_request(
        self, request: Request, request_values: list[RequestValueDTO]
    ) -> Participant:
        # Query existing participant
        participant = await self.participant_gateway.get_by_cosplay2_id(
            cosplay2_id=request.id
        )

        # Non APPROVED participants are denied...
        if request.status != RequestStatus.APPROVED:
            # ...and deleted if they are already in database
            if participant:
                await self.participant_gateway.delete(participant)
                logger.error(
                    "Participant %s deleted due to non-approved request",
                    participant.cosplay2_id,
                )
            else:
                logger.error("Request %s is not approved", request.id)
            raise NonApprovedRequest

        # Check voting title
        if not request.voting_title:
            logger.error("Request %s has no voting title, cannot proceed", request.id)
            raise RequestHasNoVotingTitle

        nomination = await self.nomination_gateway.get_by_cosplay2_id(request.topic_id)
        if nomination is None:
            logger.error("Nomination with Cosplay2 id=%s not found", request.topic_id)
            raise NonApprovedRequest

        # Convert request values to participant values
        request_values = [v for v in request_values if v.request_id == request.id]
        participant_values = [
            ParticipantValue(title=r.title, type=r.type, value=r.value)
            for r in request_values
        ]

        # Update or create participant
        if participant:
            participant = replace(
                participant,
                title=request.voting_title,
                nomination_id=nomination.id,
                voting_number=request.voting_number,
                values=participant_values,
            )
            await self.participant_gateway.save(participant)
            logger.info("Request %s updated", participant.cosplay2_id)
        else:
            participant = Participant(
                id=generate_participant_id(),
                cosplay2_id=request.id,
                title=request.voting_title,
                nomination_id=nomination.id,
                voting_number=request.voting_number,
                values=participant_values,
            )
            await self.participant_gateway.add(participant)
            logger.info("Request %s added", participant.cosplay2_id)

        return participant

    async def __call__(self) -> None:
        # Sync topics
        topics = await self.client.get_topics_list()
        topic_ids = {topic.id for topic in topics}
        for topic in topics:
            await self._process_topic(topic)

        stale_nomination_ids = (
            set(await self.nomination_gateway.list_cosplay2_ids()) - topic_ids
        )
        await self.nomination_gateway.delete_by_cosplay2_ids(list(stale_nomination_ids))

        # Sync requests and values
        requests = await self.client.get_all_requests()
        values = await self.client.get_all_values()
        request_ids = {request.id for request in requests}
        for request in requests:
            # Skip non-approved and no voting title requests
            with contextlib.suppress(RequestHasNoVotingTitle, NonApprovedRequest):
                await self._process_request(request, values)

        stale_participant_ids = (
            set(await self.participant_gateway.list_cosplay2_ids()) - request_ids
        )
        await self.participant_gateway.delete_by_cosplay2_ids(
            list(stale_participant_ids)
        )

        await self.uow.commit()
