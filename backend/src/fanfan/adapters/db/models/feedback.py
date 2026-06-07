from uuid import uuid7

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.feedback import FeedbackId
from fanfan.core.vo.user import UserId


class FeedbackORM(BaseORM):
    __tablename__ = "feedback"

    id: Mapped[FeedbackId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text())
