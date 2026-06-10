from fanfan.adapters.db.models import TicketORM
from fanfan.core.models.ticket import Ticket
from fanfan.core.vo.ticket import TicketId
from fanfan.core.vo.user import UserId


class TicketMapper:
    @staticmethod
    def from_model(model: Ticket) -> TicketORM:
        return TicketORM(
            id=model.id,
            barcode=model.barcode,
            role=model.role,
            used_by_user_id=model.used_by_user_id,
            issued_by_user_id=model.issued_by_user_id,
            ticketscloud_ticket_id=model.ticketscloud_ticket_id,
        )

    @staticmethod
    def to_model(orm: TicketORM) -> Ticket:
        return Ticket(
            id=TicketId(orm.id),
            barcode=orm.barcode,
            role=orm.role,
            used_by_user_id=UserId(orm.used_by_user_id)
            if orm.used_by_user_id is not None
            else None,
            issued_by_user_id=UserId(orm.issued_by_user_id)
            if orm.issued_by_user_id is not None
            else None,
            ticketscloud_ticket_id=orm.ticketscloud_ticket_id,
        )
