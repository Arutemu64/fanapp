import { describe, expect, it } from 'vitest';

import { getApiFailureMessage } from './errors';

const FALLBACK = 'Не удалось сохранить';

const ok = { ok: true };
const notOk = { ok: false };

describe('getApiFailureMessage', () => {
	it('returns null when the call succeeded', () => {
		expect(getApiFailureMessage(undefined, ok, FALLBACK)).toBeNull();
	});

	// The reason this helper exists: a non-2xx with no parsed error body (an
	// empty 500, a proxy error page) is a failure, and a call site testing only
	// `error` would treat it as success and carry on with missing data.
	it('reports a failure when the response is not ok but there is no error body', () => {
		expect(getApiFailureMessage(undefined, notOk, FALLBACK)).toBe(FALLBACK);
	});

	it('reports a failure when the response object is missing entirely', () => {
		expect(getApiFailureMessage(undefined, undefined, FALLBACK)).toBe(FALLBACK);
	});

	it('prefers the shared copy for a known error code over the fallback', () => {
		const message = getApiFailureMessage({ code: 'TICKET_NOT_FOUND' }, notOk, FALLBACK);

		expect(message).toBe('Билет не найден');
	});

	it('falls back when the error code has no shared copy', () => {
		const message = getApiFailureMessage({ code: 'SOME_UNMAPPED_CODE' }, notOk, FALLBACK);

		expect(message).toBe(FALLBACK);
	});

	// An error body alongside a 2xx should still be treated as a failure —
	// openapi-fetch only populates `error` when it could not produce `data`.
	it('reports a failure when an error body arrives with an ok response', () => {
		const message = getApiFailureMessage({ code: 'TICKET_NOT_FOUND' }, ok, FALLBACK);

		expect(message).toBe('Билет не найден');
	});

	it('resolves validation errors to the field-specific message', () => {
		const message = getApiFailureMessage(
			{
				code: 'VALIDATION_ERROR',
				details: { errors: [{ loc: ['body', 'password'], type: 'string_too_short' }] }
			},
			notOk,
			FALLBACK
		);

		expect(message).toBe('Проверь поле «пароль»: слишком короткое значение');
	});
});
