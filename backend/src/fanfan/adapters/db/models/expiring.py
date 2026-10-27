from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM

# These tables hold short-lived state written outside the request's unit of work
# (adapters/db/expiring/). Rows past expires_at are dead; PurgeExpiredState
# deletes them. No foreign keys: see ADR-0047.


class AuthSessionORM(BaseORM):
    """A login session, keyed by the SHA-256 of the opaque cookie token."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(Text(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuthCodeORM(BaseORM):
    """The one live email code per purpose and subject (a user id or an email)."""

    __tablename__ = "auth_codes"

    purpose: Mapped[str] = mapped_column(Text(), primary_key=True)
    subject: Mapped[str] = mapped_column(Text(), primary_key=True)
    code_hash: Mapped[str] = mapped_column(Text())
    value: Mapped[str] = mapped_column(Text())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RateLimitORM(BaseORM):
    """A fixed-window attempt counter."""

    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(Text(), primary_key=True)
    hits: Mapped[int] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CooldownORM(BaseORM):
    """A claimed cooldown window; ``token`` identifies the claim that holds it."""

    __tablename__ = "cooldowns"

    key: Mapped[str] = mapped_column(Text(), primary_key=True)
    token: Mapped[str] = mapped_column(Text())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
