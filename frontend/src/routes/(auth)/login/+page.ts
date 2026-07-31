import {
	OAUTH_ERROR_CODES,
	OAUTH_LOGIN_ERROR_PARAM,
	readOAuthErrorCode
} from '$lib/utils/oauthErrors';

import type { PageLoad } from './$types';

// The page itself fetches nothing — it only reads the one-time login error code
// the backend callback leaves on the URL when the flow did not finish.
export const load: PageLoad = ({ url }) => {
	return {
		oauthLoginError: readOAuthErrorCode(url, OAUTH_LOGIN_ERROR_PARAM, OAUTH_ERROR_CODES)
	};
};
