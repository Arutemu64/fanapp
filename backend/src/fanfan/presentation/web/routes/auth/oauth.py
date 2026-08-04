import logging
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette import status
from starlette.responses import RedirectResponse, Response

from fanfan.application.interactors.auth.authorize_telegram import (
    AuthorizeTelegram,
    AuthorizeTelegramInput,
)
from fanfan.application.interactors.auth.authorize_vk import (
    AuthorizeVk,
    AuthorizeVkInput,
)
from fanfan.application.interactors.current_user.link_telegram_account import (
    LinkTelegramAccount,
    LinkTelegramAccountInput,
)
from fanfan.application.interactors.current_user.link_vk_account import (
    LinkVkAccount,
    LinkVkAccountInput,
)
from fanfan.core.exceptions.users import (
    LinkInitiatorMismatch,
    TelegramAlreadyLinkedToAnotherUser,
    UserAlreadyHasTelegramLinked,
    UserAlreadyHasVkLinked,
    VkAlreadyLinkedToAnotherUser,
)
from fanfan.core.vo.social_identity import SocialProvider
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.oauth import (
    OAUTH_ERROR_FAILED,
    PROVIDER_ISSUERS,
    OAuthFailed,
    OAuthFlowState,
    OAuthIntent,
    TelegramClaims,
    VkClaims,
    fetch_telegram_claims,
    fetch_vk_claims,
    read_flow_state,
    start_oauth_flow,
)
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie

logger = logging.getLogger(__name__)

oauth_router = APIRouter()

# Frontend reads these one-time codes off the URL and shows a safe toast.
OAUTH_LOGIN_ERROR_QUERY_PARAM = "oauthLoginError"
OAUTH_LINK_ERROR_QUERY_PARAM = "oauthLinkError"

# Link-only outcomes the user can act on, on top of the shared cancelled/failed.
LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT = "linked_to_another_account"
LINK_ERROR_USER_ALREADY_HAS_PROVIDER = "user_already_has_provider"
LINK_ERROR_SESSION_CHANGED = "session_changed"


def build_login_redirect(error_code: str | None = None) -> RedirectResponse:
    return _build_redirect("/login", OAUTH_LOGIN_ERROR_QUERY_PARAM, error_code)


def build_profile_redirect(error_code: str | None = None) -> RedirectResponse:
    return _build_redirect("/profile", OAUTH_LINK_ERROR_QUERY_PARAM, error_code)


def _build_redirect(
    path: str, query_param: str, error_code: str | None
) -> RedirectResponse:
    redirect_url = path

    if error_code is not None:
        redirect_url = f"{redirect_url}?{urlencode({query_param: error_code})}"

    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@oauth_router.get(
    "/oauth/{provider}/start",
    summary="Start social login",
    description="Redirects the browser to the provider's OAuth page to begin signing "
    "in. The provider then calls back to the callback endpoint to finish. If the "
    "redirect cannot be built the browser goes back to the login page with an "
    "`oauthLoginError` query param instead.",
    responses={
        302: {"description": "Redirect to the provider's authorization page."},
        303: {
            "description": "The provider could not be reached. Redirects to the login "
            "page with an `oauthLoginError` query param."
        },
    },
)
@inject
async def start_social_login(
    provider: SocialProvider,
    request: Request,
    oauth: FromDishka[OAuth],
) -> Response:
    try:
        client: StarletteOAuth2App = oauth.create_client(provider.value)
        url = await build_authorization_url(
            client, request, provider, OAuthIntent.LOGIN, initiator_user_id=None
        )
    except Exception:
        # Building the redirect needs the provider's discovery document (or the
        # provider being registered at all — VK is optional). The registry is
        # APP-scoped so it is fetched once per process — this is the first login
        # after a restart running into an unreachable or unconfigured provider.
        logger.exception("Could not reach the provider to start the login")
        return build_login_redirect(OAUTH_ERROR_FAILED)

    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


# The provider stays in the path rather than the state on purpose — RFC 9700
# §4.4.2.2 wants a distinct redirect URI per issuer. See oauth.py's module
# docstring. Only the *intent* is merged into this one callback.
@oauth_router.get(
    "/oauth/{provider}/callback",
    summary="Finish a social login or account link",
    description="OAuth callback shared by both flows; which one it is comes from the "
    "intent stored in the OAuth state, never from the request. On a login it sets the "
    "session cookie and redirects to the app root; on a link it attaches the account "
    "and redirects to the profile page. Every failure also redirects, carrying an "
    "`oauthLoginError` or `oauthLinkError` query param the frontend turns into a "
    "toast; this route never answers with an error body, because the browser would "
    "render it as the page. Invoked by the provider, not called directly by the "
    "frontend.",
    responses={
        303: {
            "description": "Flow finished. Redirects to the app root or the profile "
            "page; on any failure an error query param is included."
        },
    },
)
@inject
async def oauth_callback(  # noqa: PLR0913 — all params framework-injected
    provider: SocialProvider,
    request: Request,
    config: FromDishka[WebConfig],
    oauth: FromDishka[OAuth],
    authorize_telegram: FromDishka[AuthorizeTelegram],
    link_telegram: FromDishka[LinkTelegramAccount],
    authorize_vk: FromDishka[AuthorizeVk],
    link_vk: FromDishka[LinkVkAccount],
) -> RedirectResponse:
    client: StarletteOAuth2App = oauth.create_client(provider.value)

    try:
        # Must precede the token exchange: authorize_access_token consumes the
        # state payload without returning it.
        flow_state = await read_flow_state(client, request, provider)
    except OAuthFailed as e:
        # No trustworthy intent means no idea where the user came from, so send
        # them to the login page. Safe default: nothing privileged happened.
        return build_login_redirect(e.error_code)

    match provider:
        case SocialProvider.TELEGRAM:
            return await _handle_telegram(
                client,
                request,
                flow_state,
                config,
                authorize_telegram,
                link_telegram,
            )
        case SocialProvider.VK:
            return await _handle_vk(
                client,
                request,
                flow_state,
                config,
                authorize_vk,
                link_vk,
            )


async def _handle_telegram(  # noqa: PLR0913
    client: StarletteOAuth2App,
    request: Request,
    flow_state: OAuthFlowState,
    config: WebConfig,
    authorize: AuthorizeTelegram,
    link: LinkTelegramAccount,
) -> RedirectResponse:
    try:
        claims = await fetch_telegram_claims(client, request)
    except OAuthFailed as e:
        if flow_state.intent is OAuthIntent.LINK:
            return build_profile_redirect(e.error_code)
        return build_login_redirect(e.error_code)

    if flow_state.intent is OAuthIntent.LINK:
        return await _finish_telegram_link(link, claims, flow_state)

    return await _finish_telegram_login(authorize, claims, config)


async def _handle_vk(  # noqa: PLR0913
    client: StarletteOAuth2App,
    request: Request,
    flow_state: OAuthFlowState,
    config: WebConfig,
    authorize: AuthorizeVk,
    link: LinkVkAccount,
) -> RedirectResponse:
    try:
        claims = await fetch_vk_claims(client, request)
    except OAuthFailed as e:
        if flow_state.intent is OAuthIntent.LINK:
            return build_profile_redirect(e.error_code)
        return build_login_redirect(e.error_code)

    if flow_state.intent is OAuthIntent.LINK:
        return await _finish_vk_link(link, claims, flow_state)

    return await _finish_vk_login(authorize, claims, config)


async def build_authorization_url(
    client: StarletteOAuth2App,
    request: Request,
    provider: SocialProvider,
    intent: OAuthIntent,
    initiator_user_id: UserId | None,
) -> str:
    """Mint the provider redirect for either flow, recording why it was started.

    Shared with the account-linking start route in current_user/connections.py so
    both flows put the same shape of state behind the same callback.
    """
    redirect_uri = str(request.url_for("oauth_callback", provider=provider.value))

    return await start_oauth_flow(
        client,
        request,
        redirect_uri,
        OAuthFlowState(
            intent=intent,
            issuer=PROVIDER_ISSUERS[provider],
            initiator_user_id=initiator_user_id,
        ),
    )


# ── Telegram finish helpers ──────────────────────────────────────────────


async def _finish_telegram_login(
    authorize: AuthorizeTelegram, claims: TelegramClaims, config: WebConfig
) -> RedirectResponse:
    try:
        session_id = await authorize(
            AuthorizeTelegramInput(subject=claims.sub, provider_user_id=claims.id)
        )
    except Exception:
        logger.exception("Could not create a session for a Telegram login")
        return build_login_redirect(OAUTH_ERROR_FAILED)

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response


async def _finish_telegram_link(
    link: LinkTelegramAccount,
    claims: TelegramClaims,
    flow_state: OAuthFlowState,
) -> RedirectResponse:
    if flow_state.initiator_user_id is None:
        logger.warning("Link callback carried no initiator")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    try:
        await link(
            LinkTelegramAccountInput(
                subject=claims.sub,
                provider_user_id=claims.id,
                initiator_user_id=flow_state.initiator_user_id,
            )
        )
    except TelegramAlreadyLinkedToAnotherUser:
        return build_profile_redirect(LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT)
    except UserAlreadyHasTelegramLinked:
        return build_profile_redirect(LINK_ERROR_USER_ALREADY_HAS_PROVIDER)
    except LinkInitiatorMismatch:
        return build_profile_redirect(LINK_ERROR_SESSION_CHANGED)
    except Exception:
        logger.exception("Could not link a Telegram account")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    return build_profile_redirect()


# ── VK finish helpers ────────────────────────────────────────────────────


async def _finish_vk_login(
    authorize: AuthorizeVk, claims: VkClaims, config: WebConfig
) -> RedirectResponse:
    try:
        session_id = await authorize(
            AuthorizeVkInput(
                subject=str(claims.user_id),
                provider_user_id=claims.user_id,
            )
        )
    except Exception:
        logger.exception("Could not create a session for a VK login")
        return build_login_redirect(OAUTH_ERROR_FAILED)

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookie(response, session_id, config)
    return response


async def _finish_vk_link(
    link: LinkVkAccount,
    claims: VkClaims,
    flow_state: OAuthFlowState,
) -> RedirectResponse:
    if flow_state.initiator_user_id is None:
        logger.warning("Link callback carried no initiator")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    try:
        await link(
            LinkVkAccountInput(
                subject=str(claims.user_id),
                provider_user_id=claims.user_id,
                initiator_user_id=flow_state.initiator_user_id,
            )
        )
    except VkAlreadyLinkedToAnotherUser:
        return build_profile_redirect(LINK_ERROR_LINKED_TO_ANOTHER_ACCOUNT)
    except UserAlreadyHasVkLinked:
        return build_profile_redirect(LINK_ERROR_USER_ALREADY_HAS_PROVIDER)
    except LinkInitiatorMismatch:
        return build_profile_redirect(LINK_ERROR_SESSION_CHANGED)
    except Exception:
        logger.exception("Could not link a VK account")
        return build_profile_redirect(OAUTH_ERROR_FAILED)

    return build_profile_redirect()
