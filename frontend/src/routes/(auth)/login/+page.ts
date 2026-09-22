import { listOauthProvidersOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
import {
	OAUTH_ERROR_CODES,
	OAUTH_LOGIN_ERROR_PARAM,
	readOAuthErrorCode
} from '$lib/utils/oauthErrors';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, url }) => {
	const { queryClient } = await parent();

	// Which social login buttons to show is a per-deployment backend decision — a
	// provider can be built in yet unreachable from this host (Telegram is blocked
	// on Russian hosting) — so it is read at runtime, not baked into the bundle.
	// Fire-and-forget so a stalled or captive network can't hold up first paint,
	// including the email fallback; the page fails open until the answer arrives
	// (see PasswordLoginForm).
	void queryClient.prefetchQuery(listOauthProvidersOptions());

	// The one-time login error code the backend callback leaves on the URL when the
	// flow did not finish.
	return {
		oauthLoginError: readOAuthErrorCode(url, OAUTH_LOGIN_ERROR_PARAM, OAUTH_ERROR_CODES)
	};
};
