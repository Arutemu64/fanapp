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

// Social accounts now arrive with the current user from the root layout's `/me/`
// load, so this page fetches nothing — it only reads the one-time link error
// code off the URL.
export const load: PageLoad = ({ url }) => {
	return {
		title: 'Профиль',
		oauthLinkError: readOAuthErrorCode(url, OAUTH_LINK_ERROR_PARAM, LINK_ERROR_CODES)
	};
};
