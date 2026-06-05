from fanfan.adapters.db.models import ParticipantORM, VoteORM
from fanfan.adapters.db.models.participant import ParticipantValueORM
from fanfan.application.dto.participant import ParticipantFullDTO, ParticipantVoteDTO
from fanfan.core.models.participant import Participant, ParticipantValue
from fanfan.core.vo.nomination import NominationId
from fanfan.core.vo.participant import ParticipantId


class ParticipantMapper:
    @staticmethod
    def from_model(model: Participant) -> ParticipantORM:
        return ParticipantORM(
            id=model.id,
            cosplay2_id=model.cosplay2_id,
            title=model.title,
            nomination_id=model.nomination_id,
            voting_number=model.voting_number,
            values=[
                ParticipantMapper.value_from_model(value) for value in model.values
            ],
        )

    @staticmethod
    def to_model(orm: ParticipantORM) -> Participant:
        return Participant(
            id=ParticipantId(orm.id),
            cosplay2_id=orm.cosplay2_id,
            title=orm.title,
            nomination_id=NominationId(orm.nomination_id),
            voting_number=orm.voting_number,
            values=[ParticipantMapper.value_to_model(value) for value in orm.values],
        )

    @staticmethod
    def value_from_model(model: ParticipantValue) -> ParticipantValueORM:
        return ParticipantValueORM(
            title=model.title,
            type=model.type,
            value=model.value,
        )

    @staticmethod
    def value_to_model(orm: ParticipantValueORM) -> ParticipantValue:
        return ParticipantValue(
            title=orm.title,
            type=orm.type,
            value=orm.value,
        )

    @staticmethod
    def parse_full_dto(
        participant_orm: ParticipantORM, vote_orm: VoteORM | None
    ) -> ParticipantFullDTO:
        return ParticipantFullDTO(
            id=participant_orm.id,
            title=participant_orm.title,
            voting_number=participant_orm.voting_number,
            votes_count=participant_orm.votes_count,
            user_vote=ParticipantVoteDTO(id=vote_orm.id) if vote_orm else None,
        )
