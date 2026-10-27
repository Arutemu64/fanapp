export const OAUTH_LOGIN_ERROR_PARAM = 'oauthLoginError';

export const OAUTH_LINK_ERROR_PARAM = 'oauthLinkError';

export const OAUTH_ERROR_CODES = ['cancelled', 'failed'] as const;

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

export function clearOAuthErrorParam(param: string): void {
	const nextUrl = new URL(window.location.href);
	nextUrl.searchParams.delete(param);
	window.history.replaceState(window.history.state, '', nextUrl);
}
