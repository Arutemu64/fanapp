import asyncio

from pwdlib import PasswordHash

from fanfan.application.ports.password_hasher import PasswordHasher

# Each Argon2 call allocates 64 MiB at pwdlib's defaults (m=65536 KiB), and the
# API container is capped at 256M (docker-compose.yml) on a ~130M baseline, so
# only one may run at a time. More would buy no throughput either: with p=4 a
# single hash already uses every core the 1-vCPU target host has.
MAX_CONCURRENT_HASHES = 1


class PwdlibPasswordHasher(PasswordHasher):
    # Argon2 is deliberately CPU-heavy (tens of milliseconds per call at
    # pwdlib's defaults), so it runs in a worker thread: inline, every hash
    # would stall the event loop and with it every other request and SSE
    # stream in the process (https://fastapi.tiangolo.com/async/).
    # https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
    #
    # The semaphore relies on APP scope (main/ioc/security.py): one hasher, so
    # one limit, per process.
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
