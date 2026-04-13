from fanfan.application.ports.session_store import SessionStore


class LogoutUser:
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store

    async def __call__(self, session_id: str | None) -> None:
        if session_id is None:
            return
        await self.session_store.delete_session(session_id)
