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
        # One external account can only ever be linked to one user...
        UniqueConstraint("provider", "subject"),
        # ...and one user can hold at most one identity per provider.
        UniqueConstraint("user_id", "provider"),
    )

    # No standalone index: user_id leads the (user_id, provider) unique
    # constraint above, which already covers user_id lookups.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[SocialProvider] = str_enum_column(
        SocialProvider, name="social_provider"
    )
    # The provider's stable account identifier (OIDC `sub`) — the identity key.
    subject: Mapped[str] = mapped_column()
    # The provider's native account id (Telegram's Bot API user id), used only to
    # address outbound messages. NOT NULL: both providers always supply it and a
    # login/link lacking it is refused. BIGINT because Telegram ids exceed 32 bits.
    provider_user_id: Mapped[int] = mapped_column(BigInteger)
