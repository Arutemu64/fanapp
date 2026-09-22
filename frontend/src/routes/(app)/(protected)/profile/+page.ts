import { listOauthProvidersOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
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

export const load: PageLoad = async ({ parent, url }) => {
	const { queryClient } = await parent();

	// Which providers can be *linked* is the same deployment gate the login screen
	// reads — a provider unreachable from this host offers no "connect" button. Read
	// at runtime, not baked in. An already-linked provider stays unlinkable even when
	// disabled (that row comes from the user, and the unlink route is never gated), so
	// a failure here just drops the connect affordances, never the ability to unlink.
	void queryClient.prefetchQuery(listOauthProvidersOptions());

	return {
		oauthLinkError: readOAuthErrorCode(url, OAUTH_LINK_ERROR_PARAM, LINK_ERROR_CODES),
		title: 'Профиль'
	};
};
