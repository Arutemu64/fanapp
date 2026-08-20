from fanfan.adapters.db.models import FeedbackORM
from fanfan.application.dto.feedback import FeedbackDTO, FeedbackUserDTO
from fanfan.core.models.feedback import Feedback
from fanfan.core.vo.feedback import FeedbackId
from fanfan.core.vo.user import UserId


class FeedbackMapper:
    @staticmethod
    def from_model(model: Feedback) -> FeedbackORM:
        return FeedbackORM(
            id=model.id,
            user_id=model.user_id,
            text=model.text,
        )

    @staticmethod
    def to_model(orm: FeedbackORM) -> Feedback:
        return Feedback(
            id=FeedbackId(orm.id),
            user_id=UserId(orm.user_id),
            text=orm.text,
        )

    @staticmethod
    def parse_dto(orm: FeedbackORM) -> FeedbackDTO:
        return FeedbackDTO(
            id=FeedbackId(orm.id),
            text=orm.text,
            created_at=orm.created_at,
            user=FeedbackUserDTO(
                id=UserId(orm.user.id),
                username=orm.user.username,
            ),
        )
