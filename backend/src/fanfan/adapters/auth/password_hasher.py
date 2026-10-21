import asyncio

from pwdlib import PasswordHash

from fanfan.application.ports.password_hasher import PasswordHasher


class PwdlibPasswordHasher(PasswordHasher):
    # Argon2 is deliberately CPU-heavy (tens of milliseconds per call at
    # pwdlib's defaults), so it runs in a worker thread: inline, every hash
    # would stall the event loop and with it every other request and SSE
    # stream in the process (https://fastapi.tiangolo.com/async/).
    # https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self._password_hash.hash, password)

    async def verify(self, password: str, hashed_password: str) -> bool:
        return await asyncio.to_thread(
            self._password_hash.verify, password, hashed_password
        )
