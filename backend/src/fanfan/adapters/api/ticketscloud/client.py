import logging

import httpx2

from fanfan.adapters.api.base import BaseApiClient
from fanfan.adapters.api.ticketscloud.dto.order import Order, OrdersResponse
from fanfan.adapters.api.ticketscloud.dto.refund import RefundsResponse

HTTP_NOT_FOUND = 404

logger = logging.getLogger(__name__)


class TCloudClient(BaseApiClient):
    async def get_orders(self, page: int = 1, page_size: int = 200) -> OrdersResponse:
        return await self._get(
            "resources/orders", OrdersResponse, page=page, page_size=page_size
        )

    async def get_refunds(self, page: int = 1, page_size: int = 200) -> RefundsResponse:
        return await self._get(
            "resources/refund_requests",
            RefundsResponse,
            page=page,
            page_size=page_size,
        )

    async def get_order(self, order_id: str) -> Order | None:
        # Fetch a single order by id. Returns None when the order does not
        # exist (404) so callers don't have to handle HTTP error types.
        # Other errors (auth, 5xx) still propagate.
        try:
            return await self._get(f"resources/orders/{order_id}", Order)
        except httpx2.HTTPStatusError as error:
            if error.response.status_code == HTTP_NOT_FOUND:
                return None
            raise
