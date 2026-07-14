from fanfan.adapters.db.models import ParticipantORM, VoteORM
from fanfan.application.dto.participant import ParticipantFullDTO, ParticipantVoteDTO
from fanfan.core.models.participant import Participant
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId
from fanfan.core.vo.vote import VoteId


class ParticipantMapper:
    @staticmethod
    def from_model(model: Participant) -> ParticipantORM:
        return ParticipantORM(
            id=model.id,
            cosplay2_id=model.cosplay2_id,
            title=model.title,
            nomination_id=model.nomination_id,
            voting_number=model.voting_number,
        )

    @staticmethod
    def to_model(orm: ParticipantORM) -> Participant:
        return Participant(
            id=ParticipantId(orm.id),
            cosplay2_id=orm.cosplay2_id,
            title=orm.title,
            nomination_id=NominationId(orm.nomination_id),
            voting_number=orm.voting_number,
        )

    @staticmethod
    def parse_full_dto(
        participant_orm: ParticipantORM, vote_orm: VoteORM | None
    ) -> ParticipantFullDTO:
        return ParticipantFullDTO(
            id=ParticipantId(participant_orm.id),
            title=participant_orm.title,
            voting_number=participant_orm.voting_number,
            votes_count=participant_orm.votes_count,
            user_vote=ParticipantVoteDTO(id=VoteId(vote_orm.id)) if vote_orm else None,
        )
