from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

debug_router = APIRouter(tags=["Debug"], prefix="/debug")


@debug_router.get("")
async def debug(request: Request):
    return {
        "url": str(request.url),
        "scheme": request.url.scheme,
        "headers": dict(request.headers),
    }


@debug_router.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)
