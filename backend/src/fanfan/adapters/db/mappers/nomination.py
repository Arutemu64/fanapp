from fanfan.adapters.db.models import NominationORM, VoteORM
from fanfan.application.dto.nomination import NominationVoteDTO, NominationVotingDTO
from fanfan.core.models.nomination import Nomination
from fanfan.core.vo.nomination import NominationId


class NominationMapper:
    @staticmethod
    def from_model(model: Nomination) -> NominationORM:
        return NominationORM(
            id=model.id,
            cosplay2_id=model.cosplay2_id,
            code=model.code,
            title=model.title,
            is_votable=model.is_votable,
        )

    @staticmethod
    def to_model(orm: NominationORM) -> Nomination:
        return Nomination(
            id=NominationId(orm.id),
            cosplay2_id=orm.cosplay2_id,
            code=orm.code,
            title=orm.title,
            is_votable=orm.is_votable,
        )

    @staticmethod
    def parse_voting_dto(
        nomination_orm: NominationORM, vote_orm: VoteORM | None
    ) -> NominationVotingDTO:
        nomination_orm.vote = vote_orm
        return NominationVotingDTO(
            id=nomination_orm.id,
            code=nomination_orm.code,
            title=nomination_orm.title,
            participants_count=nomination_orm.participants_count,
            user_vote=NominationVoteDTO(
                id=vote_orm.id,
                participant_id=vote_orm.participant_id,
            )
            if vote_orm
            else None,
        )
