import { CancelledError } from '@tanstack/svelte-query';
import { describe, expect, it } from 'vitest';

import { droppedConnectionError } from '#lib/testing/connection.js';

import {
	getApiErrorDetail,
	getApiFieldError,
	gotNoApiAnswer,
	isUnexpectedRequestError
} from './errors';

const CONNECTION_FAILED = 'Не удалось связаться с сервером. Попробуй ещё раз.';

function validationError(errors: Array<{ loc: Array<string | number>; type: string }>) {
	return { code: 'VALIDATION_ERROR', details: { errors } };
}

describe('getApiErrorDetail', () => {
	it('maps a known code to its copy', () => {
		expect(getApiErrorDetail({ code: 'TICKET_NOT_FOUND', details: {} })).toBe('Билет не найден');
	});

	it('treats a rejected fetch as a connection failure', async () => {
		expect(getApiErrorDetail(await droppedConnectionError())).toBe(CONNECTION_FAILED);
	});

	it('does not blame the connection for a TypeError from our own code', () => {
		expect(
			getApiErrorDetail(new TypeError("Cannot read properties of undefined (reading 'id')"))
		).toBeNull();
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

describe('gotNoApiAnswer', () => {
	it('is true for a dropped connection, a timeout and a proxy page', async () => {
		expect(gotNoApiAnswer(await droppedConnectionError())).toBe(true);
		expect(gotNoApiAnswer(new DOMException('signal timed out', 'TimeoutError'))).toBe(true);
		expect(gotNoApiAnswer('<html>502 Bad Gateway</html>')).toBe(true);
	});

	it('is false for an API error body and for a bug in our own code', () => {
		expect(gotNoApiAnswer({ code: 'INTERNAL_ERROR', details: {} })).toBe(false);
		expect(gotNoApiAnswer(new SyntaxError('Unexpected token'))).toBe(false);
	});
});

describe('isUnexpectedRequestError', () => {
	it('flags a failure in our own query code', () => {
		expect(isUnexpectedRequestError(new SyntaxError('Unexpected token'))).toBe(true);
		expect(
			isUnexpectedRequestError(new TypeError("Cannot read properties of undefined (reading 'id')"))
		).toBe(true);
	});

	it('leaves out API errors, missing answers and cancellations', async () => {
		expect(isUnexpectedRequestError({ code: 'TICKET_NOT_FOUND', details: {} })).toBe(false);
		expect(isUnexpectedRequestError(await droppedConnectionError())).toBe(false);
		expect(isUnexpectedRequestError('<html>502 Bad Gateway</html>')).toBe(false);
		expect(isUnexpectedRequestError(new DOMException('aborted', 'AbortError'))).toBe(false);
		expect(isUnexpectedRequestError(new CancelledError())).toBe(false);
	});
});
