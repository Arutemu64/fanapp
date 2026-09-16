import type { SocialProvider } from '$lib/api/generated';

import { createApiClient } from '$lib/api';
import { listOauthProviders } from '$lib/api/generated';
import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '$lib/utils/fetchTimeout';
import {
	OAUTH_ERROR_CODES,
	OAUTH_LINK_ERROR_PARAM,
	readOAuthErrorCode
} from '$lib/utils/oauthErrors';

import type { PageLoad } from './$types';

// The shared OAuth outcomes (cancelled, failed) plus the conflicts only the
// linking flow can hit.
const LINK_ERROR_CODES = [
	...OAUTH_ERROR_CODES,
	'linked_to_another_account',
	'user_already_has_provider',
	'session_changed'
] as const;

// Which providers can be *linked* is the same deployment gate the login screen
// reads — a provider unreachable from this host offers no "connect" button. Read
// at runtime, not baked in. An already-linked provider stays unlinkable even when
// disabled (that row comes from the user, and the unlink route is never gated), so
// a failure here just drops the connect affordances, never the ability to unlink.
export const load: PageLoad = async ({ url, fetch }) => {
	let enabledProviders: SocialProvider[] = [];
	try {
		const client = createApiClient();
		// Timeout-bounded so a stalled connection can't block the profile page.
		const { data, error, response } = await listOauthProviders({
			client,
			fetch,
			signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
		});
		if (error) {
			// A network failure (offline / timeout) comes back as an error with no
			// `response`; stay silent and offer no linking. Only a real API error
			// (response present) is worth logging.
			if (response) {
				console.error('Error fetching enabled OAuth providers:', error);
			}
		} else {
			enabledProviders = data.providers;
		}
	} catch {
		// Defensive: the client resolves failures into `error`, but an unexpected
		// throw must still leave the linking section empty rather than break the page.
	}

	return {
		title: 'Профиль',
		oauthLinkError: readOAuthErrorCode(url, OAUTH_LINK_ERROR_PARAM, LINK_ERROR_CODES),
		enabledProviders
	};
};
