import pytest

from fanfan.adapters.api.cosplay2.dto.requests import (
    Request,
    RequestStatus,
    RequestValueDTO,
)
from fanfan.adapters.api.cosplay2.dto.topics import Topic
from fanfan.adapters.api.cosplay2.source import Cosplay2Source
from fanfan.core.vo.participant import ValueType

pytestmark = pytest.mark.unit


class FakeCosplay2Client:
    """Stands in for Cosplay2Client, returning canned vendor DTOs (no HTTP)."""

    def __init__(
        self,
        topics: list[Topic],
        requests: list[Request],
        values: list[RequestValueDTO],
    ) -> None:
        self._topics = topics
        self._requests = requests
        self._values = values

    async def get_topics_list(self) -> list[Topic]:
        return self._topics

    async def get_all_requests(self) -> list[Request]:
        return self._requests

    async def get_all_values(self) -> list[RequestValueDTO]:
        return self._values


def _request(
    request_id: int,
    *,
    status: RequestStatus = RequestStatus.APPROVED,
    voting_title: str | None = "Title",
    topic_id: int = 1,
) -> Request:
    return Request(
        id=request_id,
        topic_id=topic_id,
        voting_number=request_id,
        voting_title=voting_title,
        status=status,
    )


async def test_fetch_nominations_maps_topics() -> None:
    source = Cosplay2Source(
        FakeCosplay2Client(
            topics=[Topic(id=1, card_code="A1", title="Best Costume")],
            requests=[],
            values=[],
        )
    )

    nominations = await source.fetch_nominations()

    assert len(nominations) == 1
    assert nominations[0].external_id == 1
    assert nominations[0].code == "A1"
    assert nominations[0].title == "Best Costume"


async def test_fetch_participants_keeps_only_approved_with_voting_title() -> None:
    source = Cosplay2Source(
        FakeCosplay2Client(
            topics=[],
            requests=[
                _request(1),  # approved + title -> kept
                _request(2, status=RequestStatus.PENDING),  # not approved -> dropped
                _request(3, voting_title=None),  # no voting title -> dropped
                _request(4, voting_title=""),  # empty title is falsy -> dropped
            ],
            values=[],
        )
    )

    participants = await source.fetch_participants()

    assert [p.external_id for p in participants] == [1]


async def test_fetch_participants_groups_values_by_request() -> None:
    source = Cosplay2Source(
        FakeCosplay2Client(
            topics=[],
            requests=[_request(1, topic_id=7)],
            values=[
                RequestValueDTO(
                    request_id=1, title="City", type=ValueType.TEXT, value="Moscow"
                ),
                RequestValueDTO(
                    request_id=1, title="Link", type=ValueType.LINK, value="http://x"
                ),
                # Belongs to another request, must not leak into request 1.
                RequestValueDTO(
                    request_id=99, title="Other", type=ValueType.TEXT, value="nope"
                ),
            ],
        )
    )

    participants = await source.fetch_participants()

    assert len(participants) == 1
    participant = participants[0]
    assert participant.nomination_external_id == 7
    assert [v.title for v in participant.values] == ["City", "Link"]
