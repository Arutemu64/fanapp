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

    @staticmethod
    def _decode(value: str | bytes) -> str:
        # The Redis client is created with decode_responses=True, so values come
        # back as str at runtime; the stubs still type them as str | bytes.
        return value.decode() if isinstance(value, bytes) else value

    async def create_session(self, user_id: UserId) -> str:
        # Keep session IDs opaque so user identity is never embedded in cookies.
        session_id = secrets.token_urlsafe(32)
        user_sessions_key = self._user_sessions_key(user_id)
        # Write the session and its index entry together so a failure can never
        # leave a valid session that is missing from the index (which would make
        # it impossible to revoke via revoke_user_sessions).
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(
                name=self._session_key(session_id),
                value=str(user_id),
                ex=self.ttl_seconds,
            )
            pipe.sadd(user_sessions_key, session_id)
            pipe.expire(user_sessions_key, self.ttl_seconds)
            await pipe.execute()
        return session_id

    async def resolve_session(self, session_id: str) -> SessionResolution:
        key = self._session_key(session_id)
        user_id = await self.redis.get(key)
        if not user_id:
            return SessionResolution(user_id=None, touched=False)

        resolved_user_id = UserId(UUID(self._decode(user_id)))
        ttl_left = await self.redis.ttl(key)
        touched = False
        if ttl_left > 0 and ttl_left <= self.touch_threshold_seconds:
            # Extend the session and its index entry together. The index set has
            # its own TTL, so refreshing only the session key would let the index
            # expire out from under a still-valid session, leaving it unrevokable.
            user_sessions_key = self._user_sessions_key(resolved_user_id)
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.expire(key, self.ttl_seconds)
                pipe.sadd(user_sessions_key, session_id)
                pipe.expire(user_sessions_key, self.ttl_seconds)
                await pipe.execute()
            touched = True

        return SessionResolution(user_id=resolved_user_id, touched=touched)

    async def delete_session(self, session_id: str) -> None:
        key = self._session_key(session_id)
        user_id = await self.redis.get(key)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            if user_id:
                pipe.srem(
                    self._user_sessions_key(UserId(UUID(self._decode(user_id)))),
                    session_id,
                )
            await pipe.execute()

    async def revoke_user_sessions(self, user_id: UserId) -> None:
        user_sessions_key = self._user_sessions_key(user_id)
        session_ids = await self.redis.smembers(user_sessions_key)
        async with self.redis.pipeline(transaction=True) as pipe:
            for sid in session_ids:
                pipe.delete(self._session_key(self._decode(sid)))
            pipe.delete(user_sessions_key)
            await pipe.execute()
