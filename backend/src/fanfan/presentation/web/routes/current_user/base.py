from fastapi import APIRouter

current_user_router = APIRouter(tags=["Current user"], prefix="/me")
