from fanfan.adapters.db.models import VoteORM
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
