import hashlib
import secrets
from datetime import timedelta
from typing import override

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fanfan.adapters.db.models import AuthSessionORM
from fanfan.application.ports.session_store import SessionResolution, SessionStore
from fanfan.core.vo.user import UserId


def _hash_token(session_id: str) -> str:
    """Store a one-way verifier, so a database dump holds no live sessions.

    https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
    """
    return hashlib.sha256(session_id.encode()).hexdigest()


class PostgresSessionStore(SessionStore):
    """Opaque session tokens, each in its own transaction off the unit of work."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        ttl_seconds: int,
        touch_threshold_seconds: int,
    ) -> None:
        self.sessions = sessions
        self.ttl = timedelta(seconds=max(1, ttl_seconds))
        self.touch_threshold = timedelta(seconds=max(1, touch_threshold_seconds))

    @override
    async def create_session(self, user_id: UserId) -> str:
        session_id = secrets.token_urlsafe(32)
        async with self.sessions.begin() as session:
            await session.execute(
                insert(AuthSessionORM).values(
                    token_hash=_hash_token(session_id),
                    user_id=user_id,
                    expires_at=func.now() + self.ttl,
                )
            )
        return session_id

    @override
    async def resolve_session(self, session_id: str) -> SessionResolution:
        token_hash = _hash_token(session_id)
        async with self.sessions.begin() as session:
            row = (
                await session.execute(
                    select(
                        AuthSessionORM.user_id,
                        (AuthSessionORM.expires_at - func.now()).label("remaining"),
                    ).where(
                        AuthSessionORM.token_hash == token_hash,
                        AuthSessionORM.expires_at > func.now(),
                    )
                )
            ).one_or_none()
            if row is None:
                return SessionResolution(user_id=None, touched=False)

            touched = row.remaining <= self.touch_threshold
            if touched:
                await session.execute(
                    update(AuthSessionORM)
                    .where(AuthSessionORM.token_hash == token_hash)
                    .values(expires_at=func.now() + self.ttl)
                )
        return SessionResolution(user_id=UserId(row.user_id), touched=touched)

    @override
    async def delete_session(self, session_id: str) -> None:
        async with self.sessions.begin() as session:
            await session.execute(
                delete(AuthSessionORM).where(
                    AuthSessionORM.token_hash == _hash_token(session_id)
                )
            )

    @override
    async def revoke_user_sessions(self, user_id: UserId) -> None:
        async with self.sessions.begin() as session:
            await session.execute(
                delete(AuthSessionORM).where(AuthSessionORM.user_id == user_id)
            )
