import {
	readTelegramErrorCode,
	TELEGRAM_LINK_ERROR_PARAM,
	TELEGRAM_OAUTH_ERROR_CODES
} from '$lib/utils/telegramOAuth';

import type { PageLoad } from './$types';

// The shared OAuth outcomes (cancelled, failed) plus the two conflicts only the
// linking flow can hit.
const TELEGRAM_LINK_ERROR_CODES = [
	...TELEGRAM_OAUTH_ERROR_CODES,
	'linked_to_another_account',
	'user_already_has_telegram'
] as const;

// Social accounts now arrive with the current user from the root layout's `/me/`
// load, so this page fetches nothing — it only reads the one-time Telegram link
// error code off the URL.
export const load: PageLoad = ({ url }) => {
	return {
		title: 'Профиль',
		telegramLinkError: readTelegramErrorCode(
			url,
			TELEGRAM_LINK_ERROR_PARAM,
			TELEGRAM_LINK_ERROR_CODES
		)
	};
};
