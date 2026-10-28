import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.nominations import NominationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.nominations import NominationNotFound
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.permission import Permission

logger = logging.getLogger(__name__)


class SetNominationVotableInput(BaseModel):
    nomination_id: NominationId
    is_votable: bool


class SetNominationVotable:
    """Include a nomination in the vote or take it out (voting:manage).

    Votes already cast stay; a nomination taken out only stops taking new ones.
    """

    def __init__(
        self,
        nomination_gateway: NominationGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        uow: UnitOfWork,
    ) -> None:
        self.nomination_gateway = nomination_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.uow = uow

    async def __call__(self, data: SetNominationVotableInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.VOTING_MANAGE
        )

        nomination = await self.nomination_gateway.get(data.nomination_id)
        if nomination is None:
            raise NominationNotFound
        if nomination.is_votable == data.is_votable:
            return

        nomination.is_votable = data.is_votable
        await self.nomination_gateway.save(nomination)
        await self.uow.commit()
        logger.info(
            "Nomination votable set to %s",
            data.is_votable,
            extra={
                "nomination_id": str(nomination.id),
                "actor_id": str(current_user.id),
            },
        )
