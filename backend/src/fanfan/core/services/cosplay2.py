import logging
from dataclasses import replace

from fanfan.adapters.api.cosplay2.dto.requests import (
    Request,
    RequestStatus,
    RequestValueDTO,
)
from fanfan.adapters.api.cosplay2.dto.topics import Topic
from fanfan.adapters.db.gateways.nominations import NominationGateway
from fanfan.adapters.db.gateways.participants import ParticipantGateway
from fanfan.core.exceptions.participants import (
    NonApprovedRequest,
    RequestHasNoVotingTitle,
)
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant, ParticipantValue
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId

logger = logging.getLogger(__name__)


class Cosplay2Service:
    def __init__(
        self,
        nomination_gateway: NominationGateway,
        participant_gateway: ParticipantGateway,
    ):
        self.nomination_gateway = nomination_gateway
        self.participant_gateway = participant_gateway

    async def process_topic(self, topic: Topic) -> Nomination:
        nomination = await self.nomination_gateway.get_nomination_by_id(
            NominationId(topic.id)
        )

        # Update or create nomination
        if nomination:
            nomination = replace(nomination, code=topic.card_code, title=topic.title)
            nomination = await self.nomination_gateway.save_nomination(nomination)
            logger.info("Nomination %s updated", nomination.id)
        else:
            nomination = Nomination(
                id=NominationId(topic.id),
                code=topic.card_code,
                title=topic.title,
                is_votable=False,
            )
            nomination = await self.nomination_gateway.add_nomination(nomination)
            logger.info("Nomination %s added", nomination.id)

        return nomination

    async def process_request(
        self, request: Request, request_values: list[RequestValueDTO]
    ) -> Participant:
        # Query existing participant
        participant = await self.participant_gateway.get_participant_by_id(
            participant_id=ParticipantId(request.id)
        )

        # Non APPROVED participants are denied...
        if request.status != RequestStatus.APPROVED:
            # ...and deleted if they are already in database
            if participant:
                await self.participant_gateway.delete_participant(participant)
                logger.error(
                    "Participant %s deleted due to non-approved request", participant.id
                )
            else:
                logger.error("Request %s is not approved", request.id)
            raise NonApprovedRequest

        # Check voting title
        if not request.voting_title:
            logger.error("Request %s has no voting title, cannot proceed", request.id)
            raise RequestHasNoVotingTitle

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
                nomination_id=NominationId(request.topic_id),
                voting_number=request.voting_number,
                values=participant_values,
            )
            await self.participant_gateway.save_participant(participant)
            logger.info("Participant %s updated", participant.id)
        else:
            participant = Participant(
                id=ParticipantId(request.id),
                title=request.voting_title,
                nomination_id=NominationId(request.topic_id),
                voting_number=request.voting_number,
                values=participant_values,
            )
            await self.participant_gateway.add_participant(participant)
            logger.info("Participant %s added", participant.id)

        return participant
