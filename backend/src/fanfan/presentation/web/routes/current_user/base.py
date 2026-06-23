from fastapi import APIRouter

from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import session_security

current_user_router = APIRouter(
    tags=["Current user"],
    prefix="/me",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)
