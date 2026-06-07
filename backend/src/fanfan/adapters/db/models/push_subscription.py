from uuid import uuid7

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


class PushSubscriptionORM(BaseORM):
    __tablename__ = "push_subs"

    id: Mapped[PushSubscriptionId] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UserId] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(unique=True)
    p256dh: Mapped[str] = mapped_column()
    auth: Mapped[str] = mapped_column()
