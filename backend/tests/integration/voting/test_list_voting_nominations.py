import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import generate_nomination_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_pages_cover_every_votable_nomination_exactly_once(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    nomination_gateway = await dishka_request.get(NominationGateway)

    expected_ids = set()
    for cosplay2_id in range(5000, 5007):
        nomination = Nomination(
            id=generate_nomination_id(),
            cosplay2_id=cosplay2_id,
            code=f"paging-{cosplay2_id}",
            title=f"Номинация {cosplay2_id}",
            is_votable=True,
        )
        await nomination_gateway.add(nomination)
        expected_ids.add(nomination.id)
    await uow.commit()

    page_size = 3
    seen_ids = []
    for offset in range(0, 9, page_size):
        page = await nomination_gateway.read_list_votable_nominations(
            pagination=Pagination(limit=page_size, offset=offset)
        )
        seen_ids.extend(dto.id for dto in page)

    assert len(seen_ids) == len(set(seen_ids))
    assert expected_ids <= set(seen_ids)
