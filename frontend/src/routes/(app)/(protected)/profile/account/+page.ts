import { m } from '#lib/paraglide/messages.js';
import {
	OAUTH_ERROR_CODES,
	OAUTH_LINK_ERROR_PARAM,
	readOAuthErrorCode
} from '#lib/utils/oauthErrors.js';

import type { PageLoad } from './$types';

// The shared OAuth outcomes (cancelled, failed) plus the conflicts only the
// linking flow can hit.
const LINK_ERROR_CODES = [
	...OAUTH_ERROR_CODES,
	'linked_to_another_account',
	'user_already_has_provider',
	'session_changed'
] as const;

export const load: PageLoad = ({ url }) => ({
	title: m.account_title(),
	oauthLinkError: readOAuthErrorCode(url, OAUTH_LINK_ERROR_PARAM, LINK_ERROR_CODES)
});
