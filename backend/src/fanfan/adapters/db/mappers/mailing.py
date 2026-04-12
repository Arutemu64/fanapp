from fanfan.adapters.db.models import MailingORM
from fanfan.application.dto.mailing import MailingDTO
from fanfan.core.models.mailing import Mailing


class MailingMapper:
    @staticmethod
    def from_model(model: Mailing) -> MailingORM:
        return MailingORM(
            id=model.id,
            status=model.status,
            by_user_id=model.by_user_id,
            sent_count=model.sent_count,
            total_count=model.total_count,
        )

    @staticmethod
    def to_model(orm: MailingORM) -> Mailing:
        return Mailing(
            id=orm.id,
            status=orm.status,
            by_user_id=orm.by_user_id,
            sent_count=orm.sent_count,
            total_count=orm.total_count,
        )

    @staticmethod
    def parse_dto(orm: MailingORM) -> MailingDTO:
        return MailingDTO(
            id=orm.id,
            status=orm.status,
            by_user_id=orm.by_user_id,
            sent_count=orm.sent_count,
            total_count=orm.total_count,
        )
