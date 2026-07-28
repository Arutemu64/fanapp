/**
 * One-time error codes the two Telegram OAuth callbacks put on the URL.
 *
 * Both callbacks are entered by a top-level browser navigation coming back from
 * Telegram, never by a fetch from here, so the backend cannot answer with an
 * error body — the browser would render the JSON as the page. It redirects with
 * a code instead. These mirror `presentation/web/telegram_oauth.py` and the two
 * routers that use it.
 */

/** Query param on `/login`, set by the login callback. */
export const TELEGRAM_LOGIN_ERROR_PARAM = 'telegramLoginError';

/** Query param on `/profile`, set by the account-linking callback. */
export const TELEGRAM_LINK_ERROR_PARAM = 'telegramLinkError';

/** Codes either callback can return, on top of its own flow-specific ones. */
export const TELEGRAM_OAUTH_ERROR_CODES = ['cancelled', 'failed'] as const;

/**
 * Read a whitelisted error code off the URL. Anything unrecognised becomes
 * `null`, so a hand-edited link can never put arbitrary text in front of the
 * user.
 */
export function readTelegramErrorCode<Code extends string>(
	url: URL,
	param: string,
	codes: readonly Code[]
): Code | null {
	const value = url.searchParams.get(param);

	if (value && (codes as readonly string[]).includes(value)) {
		return value as Code;
	}

	return null;
}

/**
 * Drop the one-time code from the address bar without navigating, so reloading
 * or sharing the URL does not replay the toast.
 */
export function clearTelegramErrorParam(param: string): void {
	const nextUrl = new URL(window.location.href);
	nextUrl.searchParams.delete(param);
	window.history.replaceState(window.history.state, '', nextUrl);
}
