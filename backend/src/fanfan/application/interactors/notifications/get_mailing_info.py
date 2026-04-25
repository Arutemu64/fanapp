from pydantic import BaseModel

from fanfan.application.dto.mailing import MailingDTO
from fanfan.application.ports.queries.mailings import MailingQuery
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId


class GetMailingInfoInput(BaseModel):
    mailing_id: MailingId


class GetMailingInfo:
    # TODO Remove?
    def __init__(self, mailing_query: MailingQuery):
        self.mailing_query = mailing_query

    async def __call__(self, data: GetMailingInfoInput) -> MailingDTO:
        mailing_data = await self.mailing_query.read_mailing(data.mailing_id)
        if mailing_data is None:
            raise MailingNotFound
        return mailing_data
