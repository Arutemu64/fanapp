from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.user import UserORM


class QuestAwardORM(UUIDPrimaryKeyMixin, BaseORM):
    __tablename__ = "quest_awards"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index(
            "ix_quest_awards_user_id_active",
            "user_id",
            postgresql_where=text("cancelled_at IS NULL"),
        ),
        Index(
            "ix_quest_awards_user_id_created_at",
            "user_id",
            text("created_at DESC"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    amount: Mapped[int]
    message: Mapped[str] = mapped_column(Text())
    awarded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    user: Mapped[UserORM] = relationship(foreign_keys=user_id, lazy="raise")
    awarder: Mapped[UserORM | None] = relationship(
        foreign_keys=awarded_by, lazy="raise"
    )
