from fanfan.adapters.db.models import MailingORM
from fanfan.core.dto.mailing import MailingDTO
from fanfan.core.models.mailing import Mailing


class MailingMapper:
    @staticmethod
    def from_model(model: Mailing) -> MailingORM:
        return MailingORM(
            id=model.id,
            total=model.total,
            is_cancelled=model.is_cancelled,
            by_user_id=model.by_user_id,
        )

    @staticmethod
    def to_model(orm: MailingORM) -> Mailing:
        return Mailing(
            id=orm.id,
            total=orm.total,
            is_cancelled=orm.is_cancelled,
            by_user_id=orm.by_user_id,
        )

    @staticmethod
    def parse_dto(orm: MailingORM) -> MailingDTO:
        return MailingDTO(
            id=orm.id,
            total=orm.total,
            is_cancelled=orm.is_cancelled,
            by_user_id=orm.by_user_id,
        )
