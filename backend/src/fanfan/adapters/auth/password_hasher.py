import asyncio

from pwdlib import PasswordHash

from fanfan.application.ports.password_hasher import PasswordHasher

MAX_CONCURRENT_HASHES = 1


class PwdlibPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._slots = asyncio.Semaphore(MAX_CONCURRENT_HASHES)

    async def hash(self, password: str) -> str:
        async with self._slots:
            return await asyncio.to_thread(self._password_hash.hash, password)

    async def verify(self, password: str, hashed_password: str) -> bool:
        async with self._slots:
            return await asyncio.to_thread(
                self._password_hash.verify, password, hashed_password
            )
