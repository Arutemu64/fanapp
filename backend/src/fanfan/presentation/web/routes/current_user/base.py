from fastapi import APIRouter

from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import require_session_docs

current_user_router = APIRouter(
    tags=["Current user"],
    prefix="/me",
    dependencies=[require_session_docs],
    responses=AUTH_RESPONSES,
)
