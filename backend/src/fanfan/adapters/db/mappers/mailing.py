from fanfan.adapters.db.models import MailingORM
from fanfan.application.dto.mailing import MailingDTO
from fanfan.core.models.mailing import Mailing
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserId


class MailingMapper:
    @staticmethod
    def from_model(model: Mailing) -> MailingORM:
        return MailingORM(
            id=model.id,
            status=model.status,
            by_user_id=model.by_user_id,
        )

    @staticmethod
    def to_model(orm: MailingORM) -> Mailing:
        return Mailing(
            id=MailingId(orm.id),
            status=orm.status,
            by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
        )

    @staticmethod
    def parse_dto(orm: MailingORM) -> MailingDTO:
        return MailingDTO(
            id=MailingId(orm.id),
            status=orm.status,
            by_user_id=UserId(orm.by_user_id) if orm.by_user_id is not None else None,
            sent_count=orm.sent_count,
            total_count=orm.total_count,
        )
