from fanfan.adapters.db.models import VoteORM
from fanfan.application.dto.vote import VoteBaseDTO
from fanfan.core.models.vote import Vote
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.user import UserId
from fanfan.core.vo.vote import VoteId


class VoteMapper:
    @staticmethod
    def from_model(model: Vote) -> VoteORM:
        return VoteORM(
            id=model.id,
            user_id=model.user_id,
            participant_id=model.participant_id,
        )

    @staticmethod
    def to_model(orm: VoteORM) -> Vote:
        return Vote(
            id=VoteId(orm.id),
            user_id=UserId(orm.user_id),
            participant_id=ParticipantId(orm.participant_id),
        )

    @staticmethod
    def parse_base_dto(vote_orm: VoteORM) -> VoteBaseDTO:
        return VoteBaseDTO(
            id=VoteId(vote_orm.id),
            user_id=UserId(vote_orm.user_id),
            participant_id=ParticipantId(vote_orm.participant_id),
        )
