import logging
from dataclasses import replace

from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.gateways.participants import ParticipantGateway
from fanfan.application.ports.sources.cosplay import (
    CosplaySource,
    ExternalNomination,
    ExternalParticipant,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.nomination import Nomination
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import generate_nomination_id
from fanfan.core.vo.participant import generate_participant_id

logger = logging.getLogger(__name__)


class SyncCosplay:
    def __init__(
        self,
        source: CosplaySource,
        uow: UnitOfWork,
        nomination_gateway: NominationGateway,
        participant_gateway: ParticipantGateway,
    ):
        self.source = source
        self.uow = uow
        self.nomination_gateway = nomination_gateway
        self.participant_gateway = participant_gateway

    async def _upsert_nomination(self, external: ExternalNomination) -> Nomination:
        nomination = await self.nomination_gateway.get_by_cosplay2_id(
            external.external_id
        )
        if nomination:
            nomination = replace(nomination, code=external.code, title=external.title)
            await self.nomination_gateway.save(nomination)
            logger.info(
                "Nomination updated", extra={"cosplay2_id": nomination.cosplay2_id}
            )
        else:
            nomination = Nomination(
                id=generate_nomination_id(),
                cosplay2_id=external.external_id,
                code=external.code,
                title=external.title,
                is_votable=False,
            )
            await self.nomination_gateway.add(nomination)
            logger.info(
                "Nomination added",
                extra={
                    "nomination_id": str(nomination.id),
                    "cosplay2_id": nomination.cosplay2_id,
                },
            )
        return nomination

    async def _upsert_participant(
        self,
        external: ExternalParticipant,
        nominations_by_external_id: dict[int, Nomination],
    ) -> None:
        # Resolve the participant's nomination from the map built this sync,
        # avoiding a DB query per participant.
        nomination = nominations_by_external_id.get(external.nomination_external_id)
        if nomination is None:
            logger.error(
                "Nomination not found for participant",
                extra={
                    "cosplay2_id": external.external_id,
                    "nomination_external_id": external.nomination_external_id,
                },
            )
            return

        participant = await self.participant_gateway.get_by_cosplay2_id(
            cosplay2_id=external.external_id
        )
        if participant:
            participant = replace(
                participant,
                title=external.voting_title,
                nomination_id=nomination.id,
                voting_number=external.voting_number,
                values=external.values,
            )
            await self.participant_gateway.save(participant)
            logger.info(
                "Participant updated", extra={"cosplay2_id": participant.cosplay2_id}
            )
        else:
            participant = Participant(
                id=generate_participant_id(),
                cosplay2_id=external.external_id,
                title=external.voting_title,
                nomination_id=nomination.id,
                voting_number=external.voting_number,
                values=external.values,
            )
            await self.participant_gateway.add(participant)
            logger.info(
                "Participant added",
                extra={
                    "participant_id": str(participant.id),
                    "cosplay2_id": participant.cosplay2_id,
                },
            )

    async def __call__(self) -> None:
        nominations = await self.source.fetch_nominations()
        nomination_ids = {nomination.external_id for nomination in nominations}
        # Keep the upserted nominations in memory so participant processing can
        # resolve a participant's nomination without a DB query per participant.
        nominations_by_external_id: dict[int, Nomination] = {}
        for external in nominations:
            nominations_by_external_id[
                external.external_id
            ] = await self._upsert_nomination(external)

        # Prune nominations the source no longer has. Guard against a
        # successful-but-empty response (a vendor hiccup): without this an empty
        # list marks every stored nomination as stale and wipes the table.
        # Leaving stale rows is recoverable; a mass delete is not.
        if nominations:
            stale_nomination_ids = (
                set(await self.nomination_gateway.list_cosplay2_ids()) - nomination_ids
            )
            await self.nomination_gateway.delete_by_cosplay2_ids(
                list(stale_nomination_ids)
            )
        else:
            logger.warning("Cosplay2 returned no nominations, skipping cleanup")

        participants = await self.source.fetch_participants()
        participant_ids = {participant.external_id for participant in participants}
        for external in participants:
            await self._upsert_participant(external, nominations_by_external_id)

        # Same empty-response guard as nominations above. The source returns only
        # participants the domain recognizes, so this sweep also removes anyone
        # whose source record is gone or is no longer a valid participant.
        if participants:
            stale_participant_ids = (
                set(await self.participant_gateway.list_cosplay2_ids())
                - participant_ids
            )
            await self.participant_gateway.delete_by_cosplay2_ids(
                list(stale_participant_ids)
            )
        else:
            logger.warning("Cosplay2 returned no participants, skipping cleanup")

        await self.uow.commit()
