import logging
from collections import defaultdict
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
        self,
        request: Request,
        request_values: list[RequestValueDTO],
        nominations_by_cosplay2_id: dict[int, Nomination],
    ) -> Participant | None:
        # Query existing participant
        participant = await self.participant_gateway.get_by_cosplay2_id(
            cosplay2_id=request.id
        )

        # Non APPROVED participants are denied...
        if request.status != RequestStatus.APPROVED:
            # ...and deleted if they are already in database
            if participant:
                await self.participant_gateway.delete(participant)
                logger.warning(
                    "Participant %s deleted due to non-approved request",
                    participant.cosplay2_id,
                )
            else:
                # A non-approved request with no stored participant is routine.
                logger.info("Request %s is not approved, skipping", request.id)
            return None

        # Check voting title
        if not request.voting_title:
            # An approved request that lost its voting title can no longer be
            # represented as a participant. Drop any stale participant so it
            # does not linger with outdated data, then skip it.
            if participant:
                await self.participant_gateway.delete(participant)
                logger.warning(
                    "Participant %s deleted due to missing voting title",
                    participant.cosplay2_id,
                )
            else:
                logger.info("Request %s has no voting title, skipping", request.id)
            return None

        # Look up the nomination in the map built from this sync's topics
        # instead of querying per request (avoids an N+1 over all requests).
        nomination = nominations_by_cosplay2_id.get(request.topic_id)
        if nomination is None:
            logger.error("Nomination with Cosplay2 id=%s not found", request.topic_id)
            return None

        # Convert request values to participant values
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
        # Keep the upserted nominations in memory so request processing can
        # resolve a request's nomination without a DB query per request.
        nominations_by_cosplay2_id: dict[int, Nomination] = {}
        for topic in topics:
            nominations_by_cosplay2_id[topic.id] = await self._process_topic(topic)

        # Prune nominations the upstream no longer has. Guard against a
        # successful-but-empty API response (a vendor hiccup returning 200 with
        # []): without this an empty topic list marks every stored nomination as
        # stale and wipes the table. Leaving stale rows is recoverable; a mass
        # delete is not.
        if topics:
            stale_nomination_ids = (
                set(await self.nomination_gateway.list_cosplay2_ids()) - topic_ids
            )
            await self.nomination_gateway.delete_by_cosplay2_ids(
                list(stale_nomination_ids)
            )
        else:
            logger.warning("Cosplay2 returned no topics, skipping nomination cleanup")

        # Sync requests and values
        requests = await self.client.get_all_requests()
        values = await self.client.get_all_values()
        request_ids = {request.id for request in requests}

        # Group values by request id once, so each request lookup is O(1)
        # instead of rescanning the full values list per request.
        values_by_request: dict[int, list[RequestValueDTO]] = defaultdict(list)
        for value in values:
            values_by_request[value.request_id].append(value)

        for request in requests:
            # Requests that cannot be turned into a participant (non-approved,
            # missing voting title, or unknown nomination) return None and are
            # skipped. Stale participants are pruned below by id, so skipping
            # here is enough.
            await self._process_request(
                request,
                values_by_request.get(request.id, []),
                nominations_by_cosplay2_id,
            )

        # Same empty-response guard as topics above: never let an empty request
        # list delete every stored participant.
        if requests:
            stale_participant_ids = (
                set(await self.participant_gateway.list_cosplay2_ids()) - request_ids
            )
            await self.participant_gateway.delete_by_cosplay2_ids(
                list(stale_participant_ids)
            )
        else:
            logger.warning(
                "Cosplay2 returned no requests, skipping participant cleanup"
            )

        await self.uow.commit()
