import typing
from uuid import UUID, uuid7

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM

if typing.TYPE_CHECKING:
    from fanfan.adapters.db.models.user import UserORM


class SocialIdentityORM(BaseORM):
    __tablename__ = "social_identities"
    __table_args__ = (
        # One external account can only ever be linked to one user...
        UniqueConstraint("provider", "provider_id"),
        # ...and one user can hold at most one identity per provider.
        UniqueConstraint("user_id", "provider"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    # No standalone index: user_id leads the (user_id, provider) unique
    # constraint above, which already covers user_id lookups.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column()
    provider_id: Mapped[str] = mapped_column()

    user: Mapped[UserORM] = relationship(back_populates="social_identities")
