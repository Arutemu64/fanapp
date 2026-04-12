from fanfan.adapters.db.models import VoteORM
from fanfan.application.dto.vote import VoteBaseDTO
from fanfan.core.models.vote import Vote


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
            id=orm.id,
            user_id=orm.user_id,
            participant_id=orm.participant_id,
        )

    @staticmethod
    def parse_base_dto(vote_orm: VoteORM) -> VoteBaseDTO:
        return VoteBaseDTO(
            id=vote_orm.id,
            user_id=vote_orm.user_id,
            participant_id=vote_orm.participant_id,
        )
