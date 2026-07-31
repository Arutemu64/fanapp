from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UpdatedAtMixin:
    """Adds an ``updated_at`` audit column tracking the last row modification.

    Only mixed into tables that actually receive UPDATEs. Append-only / audit
    tables (votes, feedback, schedule_changes, user_flags, user_permissions,
    push_subscriptions) deliberately omit it — an ``updated_at`` that can never
    move is just noise. (``social_identities`` used to be in that list; it left
    when login started refreshing ``provider_user_id`` on an existing row.)
    ``created_at`` lives on
    BaseORM and stays universal, since knowing when a row was inserted is useful
    everywhere (including append-only tables).
    """

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
