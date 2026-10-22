from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request, Response
from starlette import status

from fanfan.application.dto.settings import PublicConfigDTO
from fanfan.application.interactors.settings.get_public_config import GetPublicConfig
from fanfan.application.services.etag import compute_strong_etag
from fanfan.presentation.web.preconditions import if_none_match_hits
from fanfan.presentation.web.schemas.error import ProblemDetails

# Public, unauthenticated: the home page reads this before login and on a cold
# or offline PWA load. No session_security marker, mirroring schedule/public.
config_router = APIRouter(tags=["Config"], prefix="/config")

_ETAG_HEADERS = {
    "ETag": {
        "schema": {"type": "string"},
        "description": "Config version; send it back in If-None-Match.",
    },
}


@config_router.get(
    "",
    summary="Get public config",
    description="Returns the public festival config the SPA needs before login, "
    "with an ETag for conditional revalidation.",
    # The body is serialized here to hash it, so FastAPI must not coerce the
    # return value; `responses` keeps PublicConfigDTO in the spec.
    response_model=None,
    responses={
        200: {
            "model": PublicConfigDTO,
            "description": "Public config retrieved successfully.",
            "headers": _ETAG_HEADERS,
        },
        304: {
            "description": "Config unchanged since the client's cached version.",
            "headers": _ETAG_HEADERS,
        },
        404: {
            "model": ProblemDetails,
            "description": "Festival settings were not found.",
        },
    },
)
@inject
async def get_public_config(
    request: Request,
    interactor: FromDishka[GetPublicConfig],
) -> Response:
    payload = (await interactor()).model_dump_json()
    etag = compute_strong_etag(payload)

    # Identity-independent, so it opts out of the API-wide no-store: no-cache
    # lets the browser keep the body but revalidate it on every read, a cheap 304
    # while the config is unchanged (RFC 9111 §5.2.2.4, the schedule's ADR-0014).
    headers = {"ETag": etag, "Cache-Control": "no-cache"}

    if if_none_match_hits(request.headers.get("if-none-match"), etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)

    return Response(content=payload, media_type="application/json", headers=headers)


__all__ = ["config_router"]
