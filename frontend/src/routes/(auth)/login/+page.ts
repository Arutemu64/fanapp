import type { components } from '$lib/api/schema';

import { createApiClient } from '$lib/api';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import {
	OAUTH_ERROR_CODES,
	OAUTH_LOGIN_ERROR_PARAM,
	readOAuthErrorCode
} from '$lib/utils/oauthErrors';

import type { PageLoad } from './$types';

type SocialProvider = components['schemas']['SocialProvider'];

export const load: PageLoad = async ({ url, fetch }) => {
	// The one-time login error code the backend callback leaves on the URL when the
	// flow did not finish.
	const oauthLoginError = readOAuthErrorCode(url, OAUTH_LOGIN_ERROR_PARAM, OAUTH_ERROR_CODES);

	// Which social login buttons to show is a per-deployment backend decision — a
	// provider can be built in yet unreachable from this host (Telegram is blocked
	// on Russian hosting) — so it is read at runtime, not baked into the bundle. The
	// email option never depends on this, so any failure degrades to email-only. The
	// timeout bounds a stalled (not rejected) connection so it can't block first
	// paint — including the email fallback — on a flaky/captive network.
	let enabledProviders: SocialProvider[] = [];
	try {
		const client = createApiClient();
		const { data, error } = await client.GET('/auth/oauth/providers', {
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});
		if (error) {
			console.error('Error fetching enabled OAuth providers:', error);
		} else {
			enabledProviders = data.providers;
		}
	} catch {
		// Offline / timeout throws rather than returning `error`; show email-only.
	}

	return { oauthLoginError, enabledProviders };
};
