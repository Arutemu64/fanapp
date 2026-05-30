import sentry_sdk
from fastapi import Request

from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME


class WebIdProvider(IdProvider):
    def __init__(
        self,
        request: Request,
        session_store: SessionStore,
    ):
        self.request = request
        self.session_store = session_store

    async def get_current_user_id(self) -> UserId | None:
        session_id = self.request.cookies.get(SESSION_COOKIE_NAME)
        if session_id is None:
            sentry_sdk.set_user(None)
            return None

        resolution = await self.session_store.resolve_session(session_id)
        if resolution.touched:
            # Mark session for cookie TTL refresh in HTTP middleware.
            self.request.state.renew_session_id = session_id

        if resolution.user_id is not None:
            sentry_sdk.set_user({"id": str(resolution.user_id)})
        else:
            sentry_sdk.set_user(None)

        return resolution.user_id
