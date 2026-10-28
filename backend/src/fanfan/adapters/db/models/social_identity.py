from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.social_identity import SocialProvider


class SocialIdentityORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    __tablename__ = "social_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject"),
        UniqueConstraint("user_id", "provider"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[SocialProvider] = str_enum_column(
        SocialProvider, name="social_provider"
    )
    subject: Mapped[str] = mapped_column()
    provider_user_id: Mapped[int] = mapped_column(BigInteger)
