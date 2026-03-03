import typing
from uuid import uuid7

from sqlalchemy import UUID, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM
from fanfan.core.vo.user import UserId

if typing.TYPE_CHECKING:
    from fanfan.adapters.db.models.user import UserORM


class SocialAccountORM(BaseORM):
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_id"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id: Mapped[UserId] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column()
    provider_id: Mapped[str] = mapped_column()

    user: Mapped["UserORM"] = relationship(back_populates="social_accounts")
