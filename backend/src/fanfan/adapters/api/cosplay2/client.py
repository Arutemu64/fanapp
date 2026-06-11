import logging

from fanfan.adapters.api.base import BaseApiClient
from fanfan.adapters.api.cosplay2.dto.requests import Request, RequestValueDTO
from fanfan.adapters.api.cosplay2.dto.topics import Topic

logger = logging.getLogger(__name__)


class Cosplay2Client(BaseApiClient):
    async def get_all_requests(self) -> list[Request]:
        return await self._get("topics/get_all_requests", list[Request])

    async def get_topics_list(self) -> list[Topic]:
        return await self._get("topics/get_list", list[Topic])

    async def get_all_values(self) -> list[RequestValueDTO]:
        return await self._get("requests/get_all_values", list[RequestValueDTO])
