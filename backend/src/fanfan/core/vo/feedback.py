from typing import NewType
from uuid import UUID, uuid7

FeedbackId = NewType("FeedbackId", UUID)


def generate_feedback_id() -> FeedbackId:
    return FeedbackId(uuid7())
