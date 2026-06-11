import logging
from typing import TypeVar

from adaptix import Retort
from descanso import RestBuilder
from descanso.exceptions import ClientError
from descanso.http.aiohttp import AiohttpClient

from fanfan.adapters.api.ticketscloud.dto.order import Order, OrdersResponse
from fanfan.adapters.api.ticketscloud.dto.refund import RefundsResponse

HTTP_NOT_FOUND = 404

OutputType = TypeVar("OutputType")

logger = logging.getLogger(__name__)

rest = RestBuilder(
    request_body_dumper=Retort(),  # ty:ignore[invalid-argument-type]
    response_body_loader=Retort(),  # ty:ignore[invalid-argument-type]
    query_param_dumper=Retort(),  # ty:ignore[invalid-argument-type]
)


class TCloudClient(AiohttpClient):
    @rest.get("resources/orders")
    async def get_orders(self, page: int = 1, page_size: int = 200) -> OrdersResponse:  # ty:ignore[empty-body]
        pass

    @rest.get("resources/refund_requests")
    async def get_refunds(self, page: int = 1, page_size: int = 200) -> RefundsResponse:  # ty:ignore[empty-body]
        pass

    @rest.get("resources/orders/{order_id}")
    async def _get_order(self, order_id: str) -> Order:  # ty:ignore[empty-body]
        pass

    async def get_order(self, order_id: str) -> Order | None:
        # Fetch a single order by id. Returns None when the order does not
        # exist (404) so callers don't have to handle the HTTP client's
        # exception types. Other errors (auth, 5xx) still propagate.
        try:
            return await self._get_order(order_id)
        except ClientError as error:
            if error.status_code == HTTP_NOT_FOUND:
                return None
            raise
