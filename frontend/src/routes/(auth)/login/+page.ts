import type { SocialProvider } from '$lib/api/generated';

import { createApiClient } from '$lib/api';
import { listOauthProviders } from '$lib/api/generated';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import {
	OAUTH_ERROR_CODES,
	OAUTH_LOGIN_ERROR_PARAM,
	readOAuthErrorCode
} from '$lib/utils/oauthErrors';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url, fetch }) => {
	// The one-time login error code the backend callback leaves on the URL when the
	// flow did not finish.
	const oauthLoginError = readOAuthErrorCode(url, OAUTH_LOGIN_ERROR_PARAM, OAUTH_ERROR_CODES);

	// Which social login buttons to show is a per-deployment backend decision — a
	// provider can be built in yet unreachable from this host (Telegram is blocked
	// on Russian hosting) — so it is read at runtime, not baked into the bundle. The
	// timeout bounds a stalled (not rejected) connection so it can't block first
	// paint — including the email fallback — on a flaky/captive network.
	//
	// `null` means "couldn't determine", which is NOT the same as "none enabled": a
	// timed-out or errored probe must not hide every social button, or a social-only
	// account (no password, and its OAuth email was never stored) loses its only way
	// in. The page fails open on `null` and shows all known providers; a disabled one
	// is still rejected by its start endpoint, so the worst case is a handled error,
	// never a lockout. An authoritative empty list stays empty.
	let enabledProviders: SocialProvider[] | null = null;
	try {
		const client = createApiClient();
		const { data, error, response } = await listOauthProviders({
			client,
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});
		if (error) {
			// A network failure (offline / timeout) comes back as an error with no
			// `response`; stay silent and leave `null` to fail open. Only a real API
			// error (response present) is worth logging.
			if (response) {
				console.error('Error fetching enabled OAuth providers:', error);
			}
		} else {
			enabledProviders = data.providers;
		}
	} catch {
		// Defensive: the client resolves failures into `error`, but an unexpected
		// throw must still leave `null` to fail open rather than break the login page.
	}

	return { oauthLoginError, enabledProviders };
};
