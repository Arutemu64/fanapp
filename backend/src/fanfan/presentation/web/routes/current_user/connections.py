import logging

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.current_user.unlink_telegram_account import (
    UnlinkTelegramAccount,
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
    client: StarletteOAuth2App = oauth.create_client(provider.value)

    try:
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


# Not `/{provider}` like the route above: the rule this enforces ("you still need
# an email to sign in with") names Telegram, and generalizing it to "you may not
# remove your last way in" is a decision that needs VK's real flows in front of
# it. See UnlinkTelegramAccount.
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
            "description": "Email is required before unlinking.",
        },
    },
)
@inject
async def unlink_telegram_account(
    interactor: FromDishka[UnlinkTelegramAccount],
) -> None:
    await interactor()
