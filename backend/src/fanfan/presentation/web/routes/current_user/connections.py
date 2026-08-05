import logging

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.current_user.unlink_social_account import (
    UnlinkSocialAccount,
    UnlinkSocialAccountInput,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.oauth import OAUTH_ERROR_FAILED, OAuthIntent
from fanfan.presentation.web.routes.auth.oauth import (
    build_authorization_url,
    build_profile_redirect,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

logger = logging.getLogger(__name__)

connections_router = APIRouter(prefix="/connections")


@connections_router.get(
    "/{provider}",
    summary="Start account linking",
    description="Redirects the browser to the provider's OAuth page to begin linking "
    "the account to the current user. The provider then calls back to the shared "
    "callback (`/auth/oauth/{provider}/callback`) to finish. If the redirect cannot be "
    "built the browser goes back to the profile page with an `oauthLinkError` query "
    "param instead.",
    responses={
        302: {"description": "Redirect to the provider's authorization page."},
        303: {
            "description": "The provider could not be reached. Redirects to the "
            "profile page with an `oauthLinkError` query param."
        },
    },
)
@inject
async def start_account_link(
    provider: SocialProvider,
    request: Request,
    oauth: FromDishka[OAuth],
    current_user_provider: FromDishka[CurrentUserProvider],
) -> Response:
    try:
        client: StarletteOAuth2App = oauth.create_client(provider.value)
        # Recorded in the OAuth state and compared against the session at the
        # callback, so signing in as somebody else mid-flow cannot retarget the
        # link. require_user also keeps an anonymous browser out of this route.
        current_user = await current_user_provider.require_user()
        url = await build_authorization_url(
            client,
            request,
            provider,
            OAuthIntent.LINK,
            initiator_user_id=current_user.id,
        )
    except Exception:
        # Building the redirect needs the provider's discovery document. The
        # registry is APP-scoped so it is fetched once per process — this is the
        # first linking attempt after a restart running into an unreachable
        # provider, or a discovery document we cannot parse.
        logger.exception("Could not reach the provider to start account linking")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


# Two thin endpoints share one interactor: keeping a distinct path per provider
# preserves the frontend's typed client calls (and the per-provider redirect URI
# story of ADR-0012), while the unlink logic lives in one place.
@connections_router.delete(
    "/telegram",
    status_code=204,
    summary="Unlink Telegram account",
    description="Unlinks the Telegram account from the currently authenticated user.",
    responses={
        204: {"description": "Telegram account unlinked successfully."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Cannot remove the user's last remaining sign-in method.",
        },
    },
)
@inject
async def unlink_telegram_account(
    interactor: FromDishka[UnlinkSocialAccount],
) -> None:
    await interactor(UnlinkSocialAccountInput(provider=SocialProvider.TELEGRAM))


@connections_router.delete(
    "/vk",
    status_code=204,
    summary="Unlink VK account",
    description="Unlinks the VK account from the currently authenticated user.",
    responses={
        204: {"description": "VK account unlinked successfully."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Cannot remove the user's last remaining sign-in method.",
        },
    },
)
@inject
async def unlink_vk_account(
    interactor: FromDishka[UnlinkSocialAccount],
) -> None:
    await interactor(UnlinkSocialAccountInput(provider=SocialProvider.VK))
