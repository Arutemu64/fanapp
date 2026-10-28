import logging

from authlib.integrations.starlette_client import OAuth
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.dto.user import VkMessagesStatusDTO
from fanfan.application.interactors.current_user.check_vk_messages_allowed import (
    CheckVkMessagesAllowed,
)
from fanfan.application.interactors.current_user.unlink_social_account import (
    UnlinkSocialAccount,
    UnlinkSocialAccountInput,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.oauth import (
    OAUTH_ERROR_FAILED,
    OAuthIntent,
    create_oauth_client,
)
from fanfan.presentation.web.routes.auth.oauth import (
    build_authorization_url,
    build_profile_redirect,
)
from fanfan.presentation.web.schemas.error import ProblemDetails

logger = logging.getLogger(__name__)

connections_router = APIRouter(prefix="/connections")


@connections_router.get(
    "/{provider}",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
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
    config: FromDishka[WebConfig],
) -> Response:
    if provider not in config.enabled_oauth_providers:
        logger.info(
            "Rejected account link for a disabled provider",
            extra={"provider": provider.value},
        )
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    try:
        client = create_oauth_client(oauth, provider)
        current_user = await current_user_provider.require_user()
        url = await build_authorization_url(
            client,
            request,
            provider,
            OAuthIntent.LINK,
            initiator_user_id=current_user.id,
        )
    except Exception:
        logger.exception("Could not reach the provider to start account linking")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@connections_router.delete(
    "/{provider}",
    status_code=204,
    summary="Unlink social account",
    description="Unlinks the provider's account from the currently authenticated user.",
    responses={
        204: {"description": "Account unlinked successfully."},
        404: {"model": ProblemDetails, "description": "User not found."},
        409: {
            "model": ProblemDetails,
            "description": "Cannot remove the user's last remaining sign-in method.",
        },
    },
)
@inject
async def unlink_social_account(
    provider: SocialProvider,
    interactor: FromDishka[UnlinkSocialAccount],
) -> None:
    await interactor(UnlinkSocialAccountInput(provider=provider))


@connections_router.post(
    "/vk/messages-check",
    summary="Check VK community messages",
    description="Asks VK whether its community may message the current user's linked "
    "VK account, stores the answer and returns it. Repeated calls within a few "
    "seconds return the stored answer without asking VK.",
    responses={
        200: {"description": "The current answer; null if never checked."},
        404: {"model": ProblemDetails, "description": "No VK account is linked."},
    },
)
@inject
async def check_vk_messages_allowed(
    interactor: FromDishka[CheckVkMessagesAllowed],
) -> VkMessagesStatusDTO:
    return await interactor()
