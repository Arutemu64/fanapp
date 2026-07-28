import {
	readTelegramErrorCode,
	TELEGRAM_LOGIN_ERROR_PARAM,
	TELEGRAM_OAUTH_ERROR_CODES
} from '$lib/utils/telegramOAuth';

import type { PageLoad } from './$types';

// The page itself fetches nothing — it only reads the one-time Telegram login
// error code the backend callback leaves on the URL when the flow did not
// finish.
export const load: PageLoad = ({ url }) => {
	return {
		telegramLoginError: readTelegramErrorCode(
			url,
			TELEGRAM_LOGIN_ERROR_PARAM,
			TELEGRAM_OAUTH_ERROR_CODES
		)
	};
};
