from typing import NewType
from uuid import UUID, uuid7

ParticipantId = NewType("ParticipantId", UUID)


def generate_participant_id() -> ParticipantId:
    return ParticipantId(uuid7())
