from typing import override
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.core.vo.user import UserRole


class TicketBatchORM(UUIDPrimaryKeyMixin, BaseORM):
    """One organizer request that generated tickets; its id comes from the client."""

    __tablename__ = "ticket_batches"

    role: Mapped[UserRole] = str_enum_column(UserRole, name="userrole")
    amount: Mapped[int]
    issued_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    @override
    def __str__(self) -> str:
        return str(self.id)
