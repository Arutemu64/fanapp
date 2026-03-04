import contextlib

from fanfan.adapters.api.cosplay2.client import Cosplay2Client
from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.core.exceptions.participants import (
    NonApprovedRequest,
    RequestHasNoVotingTitle,
)
from fanfan.core.services.cosplay2 import Cosplay2Service


class SyncCosplay2:
    def __init__(
        self,
        client: Cosplay2Client,
        config: Cosplay2Config,
        cosplay2_service: Cosplay2Service,
        uow: UnitOfWork,
    ):
        self.client = client
        self.config = config
        self.cosplay2_service = cosplay2_service
        self.uow = uow

    async def __call__(self):
        async with self.uow:
            # Sync topics
            topics = await self.client.get_topics_list()
            topic_ids = {topic.id for topic in topics}
            for topic in topics:
                await self.cosplay2_service.process_topic(topic)

            stale_nomination_ids = (
                set(
                    await self.cosplay2_service.nomination_gateway.list_nomination_cosplay2_ids()
                )
                - topic_ids
            )
            await self.cosplay2_service.nomination_gateway.delete_nominations_by_cosplay2_ids(
                list(stale_nomination_ids)
            )

            # Sync requests and values
            requests = await self.client.get_all_requests()
            values = await self.client.get_all_values()
            request_ids = {request.id for request in requests}
            for request in requests:
                # Skip non-approved and no voting title requests
                with contextlib.suppress(RequestHasNoVotingTitle, NonApprovedRequest):
                    await self.cosplay2_service.process_request(request, values)

            stale_participant_ids = (
                set(
                    await self.cosplay2_service.participant_gateway.list_participant_cosplay2_ids()
                )
                - request_ids
            )
            await self.cosplay2_service.participant_gateway.delete_participants_by_cosplay2_ids(
                list(stale_participant_ids)
            )

            await self.uow.commit()
