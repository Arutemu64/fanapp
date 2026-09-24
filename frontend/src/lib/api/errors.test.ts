import { describe, expect, it } from 'vitest';

import { getApiErrorDetail, getApiFieldError } from './errors';

const CONNECTION_FAILED = 'Не удалось связаться с сервером. Попробуй ещё раз.';

function validationError(errors: Array<{ loc: Array<string | number>; type: string }>) {
	return { code: 'VALIDATION_ERROR', details: { errors } };
}

describe('getApiErrorDetail', () => {
	it('maps a known code to its copy', () => {
		expect(getApiErrorDetail({ code: 'TICKET_NOT_FOUND', details: {} })).toBe('Билет не найден');
	});

	it('treats a rejected fetch as a connection failure', () => {
		expect(getApiErrorDetail(new TypeError('Failed to fetch'))).toBe(CONNECTION_FAILED);
	});

	it('treats a timed-out request as a connection failure', () => {
		expect(getApiErrorDetail(new DOMException('signal timed out', 'TimeoutError'))).toBe(
			CONNECTION_FAILED
		);
	});

	it('says nothing about a deliberate abort', () => {
		expect(getApiErrorDetail(new DOMException('aborted', 'AbortError'))).toBeNull();
	});

	it('never passes a non-JSON error body through as copy', () => {
		expect(getApiErrorDetail('<html>502 Bad Gateway</html>')).toBeNull();
	});
});

describe('getApiFieldError', () => {
	it('returns the reason for the named body field', () => {
		const error = validationError([{ loc: ['body', 'username'], type: 'string_too_short' }]);
		expect(getApiFieldError(error, 'username')).toBe('Слишком короткое значение');
	});

	it('matches a field inside a list by its name, not the index', () => {
		const error = validationError([{ loc: ['body', 'roles', 0], type: 'enum' }]);
		expect(getApiFieldError(error, 'roles')).toBe('Неверный формат');
	});

	it('keeps a field that is itself named like the location', () => {
		const error = validationError([{ loc: ['body', 'body'], type: 'string_too_short' }]);
		expect(getApiFieldError(error, 'body')).toBe('Слишком короткое значение');
	});

	it('ignores errors about other fields', () => {
		const error = validationError([{ loc: ['body', 'email'], type: 'missing' }]);
		expect(getApiFieldError(error, 'password')).toBeNull();
	});

	it('ignores error codes other than VALIDATION_ERROR', () => {
		expect(getApiFieldError({ code: 'INVALID_EMAIL', details: {} }, 'email')).toBeNull();
	});
});
