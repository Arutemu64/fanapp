from uuid import uuid7

import pytest

from fanfan.core.models.vote import Vote
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId

pytestmark = pytest.mark.unit


def test_create_sets_fields():
    user_id = UserId(uuid7())
    participant_id = ParticipantId(uuid7())

    vote = Vote.create(user_id=user_id, participant_id=participant_id)

    assert vote.user_id == user_id
    assert vote.participant_id == participant_id


def test_create_generates_unique_ids():
    user_id = UserId(uuid7())
    participant_id = ParticipantId(uuid7())

    first = Vote.create(user_id=user_id, participant_id=participant_id)
    second = Vote.create(user_id=user_id, participant_id=participant_id)

    assert first.id != second.id
