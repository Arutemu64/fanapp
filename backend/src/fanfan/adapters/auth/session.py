import secrets
from uuid import UUID

from redis.asyncio import Redis

from fanfan.application.ports.session_store import SessionResolution, SessionStore
from fanfan.core.vo.user import UserId


class SessionManager(SessionStore):
    """Stores short opaque session identifiers in Redis."""

    def __init__(self, redis: Redis, ttl_seconds: int, touch_threshold_seconds: int):
        self.redis = redis
        self.ttl_seconds = max(1, ttl_seconds)
        self.touch_threshold_seconds = max(1, touch_threshold_seconds)

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"auth:session:{session_id}"

    @staticmethod
    def _user_sessions_key(user_id: UserId) -> str:
        return f"auth:user-sessions:{user_id}"

    async def create_session(self, user_id: UserId) -> str:
        # Keep session IDs opaque so user identity is never embedded in cookies.
        session_id = secrets.token_urlsafe(32)
        user_sessions_key = self._user_sessions_key(user_id)
        await self.redis.set(
            name=self._session_key(session_id),
            value=str(user_id),
            ex=self.ttl_seconds,
        )
        await self.redis.sadd(user_sessions_key, session_id)
        await self.redis.expire(user_sessions_key, self.ttl_seconds)
        return session_id

    async def resolve_session(self, session_id: str) -> SessionResolution:
        key = self._session_key(session_id)
        user_id = await self.redis.get(key)
        if not user_id:
            return SessionResolution(user_id=None, touched=False)

        ttl_left = await self.redis.ttl(key)
        touched = False
        if ttl_left > 0 and ttl_left <= self.touch_threshold_seconds:
            await self.redis.expire(key, self.ttl_seconds)
            touched = True

        return SessionResolution(
            user_id=UserId(
                UUID(user_id.decode() if isinstance(user_id, bytes) else user_id)
            ),
            touched=touched,
        )

    async def delete_session(self, session_id: str) -> None:
        key = self._session_key(session_id)
        user_id = await self.redis.get(key)
        await self.redis.delete(key)
        if user_id:
            user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id
            await self.redis.srem(
                self._user_sessions_key(UserId(UUID(user_id_str))), session_id
            )

    async def revoke_user_sessions(self, user_id: UserId) -> None:
        user_sessions_key = self._user_sessions_key(user_id)
        session_ids = await self.redis.smembers(user_sessions_key)
        if session_ids:
            await self.redis.delete(
                *(
                    self._session_key(sid.decode() if isinstance(sid, bytes) else sid)
                    for sid in session_ids
                )
            )
        await self.redis.delete(user_sessions_key)
