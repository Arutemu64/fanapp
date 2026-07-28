import { describe, expect, it } from 'vitest';

import {
	readTelegramErrorCode,
	TELEGRAM_LINK_ERROR_PARAM,
	TELEGRAM_OAUTH_ERROR_CODES
} from './telegramOAuth';

/** The profile page's set: the shared outcomes plus its own conflicts. */
const LINK_CODES = [
	...TELEGRAM_OAUTH_ERROR_CODES,
	'linked_to_another_account',
	'user_already_has_telegram'
] as const;

function urlWith(value: string) {
	return new URL(`https://example.com/profile?${TELEGRAM_LINK_ERROR_PARAM}=${value}`);
}

describe('readTelegramErrorCode', () => {
	it('returns a whitelisted code', () => {
		expect(readTelegramErrorCode(urlWith('cancelled'), TELEGRAM_LINK_ERROR_PARAM, LINK_CODES)).toBe(
			'cancelled'
		);
	});

	it('returns null when the param is absent', () => {
		const url = new URL('https://example.com/profile');

		expect(readTelegramErrorCode(url, TELEGRAM_LINK_ERROR_PARAM, LINK_CODES)).toBeNull();
	});

	it('returns null when the param is empty', () => {
		expect(readTelegramErrorCode(urlWith(''), TELEGRAM_LINK_ERROR_PARAM, LINK_CODES)).toBeNull();
	});

	// The whole point of the whitelist: the code reaches the page from a URL the
	// user can edit, and the page turns it straight into on-screen copy.
	it('rejects a code outside the whitelist', () => {
		const injected = encodeURIComponent('Введи пароль на example.com');

		expect(
			readTelegramErrorCode(urlWith(injected), TELEGRAM_LINK_ERROR_PARAM, LINK_CODES)
		).toBeNull();
	});

	it('rejects a code belonging to the other flow', () => {
		const url = urlWith('cancelled');

		expect(readTelegramErrorCode(url, 'telegramLoginError', LINK_CODES)).toBeNull();
	});
});
