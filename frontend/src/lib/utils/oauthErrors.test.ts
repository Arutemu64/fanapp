import { describe, expect, it } from 'vitest';

import { OAUTH_ERROR_CODES, OAUTH_LINK_ERROR_PARAM, readOAuthErrorCode } from './oauthErrors';

/** The profile page's set: the shared outcomes plus its own conflicts. */
const LINK_CODES = [
	...OAUTH_ERROR_CODES,
	'linked_to_another_account',
	'user_already_has_telegram',
	'session_changed'
] as const;

function urlWith(value: string) {
	return new URL(`https://example.com/profile?${OAUTH_LINK_ERROR_PARAM}=${value}`);
}

describe('readOAuthErrorCode', () => {
	it('returns a whitelisted code', () => {
		expect(readOAuthErrorCode(urlWith('cancelled'), OAUTH_LINK_ERROR_PARAM, LINK_CODES)).toBe(
			'cancelled'
		);
	});

	it('returns null when the param is absent', () => {
		const url = new URL('https://example.com/profile');

		expect(readOAuthErrorCode(url, OAUTH_LINK_ERROR_PARAM, LINK_CODES)).toBeNull();
	});

	it('returns null when the param is empty', () => {
		expect(readOAuthErrorCode(urlWith(''), OAUTH_LINK_ERROR_PARAM, LINK_CODES)).toBeNull();
	});

	// The whole point of the whitelist: the code reaches the page from a URL the
	// user can edit, and the page turns it straight into on-screen copy.
	it('rejects a code outside the whitelist', () => {
		const injected = encodeURIComponent('Введи пароль на example.com');

		expect(readOAuthErrorCode(urlWith(injected), OAUTH_LINK_ERROR_PARAM, LINK_CODES)).toBeNull();
	});

	it('rejects a code belonging to the other flow', () => {
		const url = urlWith('cancelled');

		expect(readOAuthErrorCode(url, 'oauthLoginError', LINK_CODES)).toBeNull();
	});
});
