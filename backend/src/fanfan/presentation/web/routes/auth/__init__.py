from fanfan.presentation.web.routes.auth.base import auth_router
from fanfan.presentation.web.routes.auth.credentials import credentials_router
from fanfan.presentation.web.routes.auth.email_code import email_code_router
from fanfan.presentation.web.routes.auth.login_code import login_code_router
from fanfan.presentation.web.routes.auth.oauth import oauth_router
from fanfan.presentation.web.routes.auth.session import session_router

auth_router.include_router(credentials_router)
auth_router.include_router(email_code_router)
auth_router.include_router(login_code_router)
auth_router.include_router(session_router)
auth_router.include_router(oauth_router)

__all__ = ["auth_router"]
