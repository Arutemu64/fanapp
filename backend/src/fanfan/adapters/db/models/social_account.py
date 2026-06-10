import typing
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM

if typing.TYPE_CHECKING:
    from fanfan.adapters.db.models.user import UserORM


class SocialIdentityORM(BaseORM):
    # TODO Rename table
    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_id"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column()
    provider_id: Mapped[str] = mapped_column()

    user: Mapped[UserORM] = relationship(back_populates="social_accounts")
