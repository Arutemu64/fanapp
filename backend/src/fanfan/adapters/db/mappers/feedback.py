from fanfan.adapters.db.models import FeedbackORM
from fanfan.core.models.feedback import Feedback


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
            id=orm.id,
            user_id=orm.user_id,
            text=orm.text,
        )
