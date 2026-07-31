/**
 * One-time error codes the OAuth callback puts on the URL.
 *
 * Login and account linking share one backend callback and are told apart by an
 * intent stored in the OAuth state. That callback is entered by a top-level
 * browser navigation coming back from the provider, never by a fetch from here,
 * so the backend cannot answer with an error body — the browser would render the
 * JSON as the page. It redirects with a code instead, to `/login` or `/profile`
 * depending on which flow was running. These mirror `presentation/web/oauth.py`
 * and `presentation/web/routes/auth/oauth.py`.
 */

/** Query param on `/login`, set when a login flow did not finish. */
export const OAUTH_LOGIN_ERROR_PARAM = 'oauthLoginError';

/** Query param on `/profile`, set when a linking flow did not finish. */
export const OAUTH_LINK_ERROR_PARAM = 'oauthLinkError';

/** Codes either flow can return, on top of the linking-specific ones. */
export const OAUTH_ERROR_CODES = ['cancelled', 'failed'] as const;

/**
 * Read a whitelisted error code off the URL. Anything unrecognised becomes
 * `null`, so a hand-edited link can never put arbitrary text in front of the
 * user.
 */
export function readOAuthErrorCode<Code extends string>(
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
export function clearOAuthErrorParam(param: string): void {
	const nextUrl = new URL(window.location.href);
	nextUrl.searchParams.delete(param);
	window.history.replaceState(window.history.state, '', nextUrl);
}
