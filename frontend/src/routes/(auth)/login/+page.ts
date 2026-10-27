import {
	OAUTH_ERROR_CODES,
	OAUTH_LOGIN_ERROR_PARAM,
	readOAuthErrorCode
} from '#lib/utils/oauthErrors.js';

import type { PageLoad } from './$types';

export const load: PageLoad = ({ url }) => {
	const oauthLoginError = readOAuthErrorCode(url, OAUTH_LOGIN_ERROR_PARAM, OAUTH_ERROR_CODES);

	return { oauthLoginError };
};
