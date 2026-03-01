from pydantic import BaseModel

from fanfan.adapters.db.gateways.mailings import MailingGateway
from fanfan.core.dto.mailing import MailingDTO
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.vo.mailing import MailingId


class GetMailingInfoCommand(BaseModel):
    mailing_id: MailingId


class GetMailingInfo:
    # TODO Remove?
    def __init__(self, mailing_gateway: MailingGateway):
        self.mailing_gateway = mailing_gateway

    async def __call__(self, data: GetMailingInfoCommand) -> MailingDTO:
        mailing_data = await self.mailing_gateway.read_mailing(data.mailing_id)
        if mailing_data is None:
            raise MailingNotFound
        return mailing_data
