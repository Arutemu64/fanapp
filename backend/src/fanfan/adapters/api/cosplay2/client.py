import logging

from adaptix import Retort
from descanso import RestBuilder
from descanso.http.aiohttp import AiohttpClient

from fanfan.adapters.api.cosplay2.dto.requests import Request, RequestValueDTO
from fanfan.adapters.api.cosplay2.dto.topics import Topic

logger = logging.getLogger(__name__)

rest = RestBuilder(
    request_body_dumper=Retort(),  # ty:ignore[invalid-argument-type]
    response_body_loader=Retort(),  # ty:ignore[invalid-argument-type]
    query_param_dumper=Retort(),  # ty:ignore[invalid-argument-type]
)


class Cosplay2Client(AiohttpClient):
    @rest.get("topics/get_all_requests")
    async def get_all_requests(self) -> list[Request]:  # ty:ignore[empty-body]
        pass

    @rest.get("topics/get_list")
    async def get_topics_list(self) -> list[Topic]:  # ty:ignore[empty-body]
        pass

    @rest.get("requests/get_all_values")
    async def get_all_values(self) -> list[RequestValueDTO]:  # ty:ignore[empty-body]
        pass
