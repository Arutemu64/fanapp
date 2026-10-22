import { CancelledError } from '@tanstack/svelte-query';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { droppedConnectionError } from '#lib/testing/connection.js';

import {
	fetchRecordingConnectionFailures,
	getApiErrorDetail,
	getApiFieldError,
	gotNoApiAnswer,
	isConnectionFailure,
	isUnexpectedRequestError,
	throwApiError
} from './errors';

const CONNECTION_FAILED = 'Не удалось связаться с сервером. Попробуй ещё раз.';

function validationError(
	errors: Array<{ loc: Array<string | number>; type: string; ctx?: Record<string, unknown> }>
) {
	return { code: 'VALIDATION_ERROR', errors };
}

describe('getApiErrorDetail', () => {
	it('maps a known code to its copy', () => {
		expect(getApiErrorDetail({ code: 'TICKET_NOT_FOUND' })).toBe('Билет не найден');
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

	it('points a schedule-file error at the cell to fix', () => {
		const error = {
			code: 'INVALID_SCHEDULE_FILE',
			reason: 'EMPTY_CELL',
			column: 'C',
			row: 4
		};
		expect(getApiErrorDetail(error)).toContain('4');
	});

	it('falls back to the generic schedule-file copy for an unknown reason', () => {
		const unknown = { code: 'INVALID_SCHEDULE_FILE', reason: 'NEW_REASON' };
		const unreadable = { code: 'INVALID_SCHEDULE_FILE', reason: 'UNREADABLE_FILE' };
		expect(getApiErrorDetail(unknown)).toBe(getApiErrorDetail(unreadable));
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

	it('names the limit the input broke when the server sends it', () => {
		const error = validationError([
			{ loc: ['body', 'body'], type: 'string_too_long', ctx: { max_length: 500 } }
		]);
		expect(getApiFieldError(error, 'body')).toBe('Максимум 500 символов');
	});

	it('ignores errors about other fields', () => {
		const error = validationError([{ loc: ['body', 'email'], type: 'missing' }]);
		expect(getApiFieldError(error, 'password')).toBeNull();
	});

	it('ignores error codes other than VALIDATION_ERROR', () => {
		expect(getApiFieldError({ code: 'INVALID_EMAIL' }, 'email')).toBeNull();
	});
});

describe('gotNoApiAnswer', () => {
	it('is true for a dropped connection, a timeout and a proxy page', async () => {
		expect(gotNoApiAnswer(await droppedConnectionError())).toBe(true);
		expect(gotNoApiAnswer(new DOMException('signal timed out', 'TimeoutError'))).toBe(true);
		expect(gotNoApiAnswer('<html>502 Bad Gateway</html>')).toBe(true);
	});

	it('is false for an API error body and for a bug in our own code', () => {
		expect(gotNoApiAnswer({ code: 'INTERNAL_ERROR' })).toBe(false);
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
		expect(isUnexpectedRequestError({ code: 'TICKET_NOT_FOUND' })).toBe(false);
		expect(isUnexpectedRequestError(await droppedConnectionError())).toBe(false);
		expect(isUnexpectedRequestError('<html>502 Bad Gateway</html>')).toBe(false);
		expect(isUnexpectedRequestError(new DOMException('aborted', 'AbortError'))).toBe(false);
		expect(isUnexpectedRequestError(new CancelledError())).toBe(false);
	});
});

describe('fetchRecordingConnectionFailures', () => {
	afterEach(() => vi.unstubAllGlobals());

	// What `fetch` resolves with when the connection drops after the headers: a
	// body whose stream errors the way the browser's does (Chromium rejects the
	// read with "TypeError: Failed to fetch").
	function stubDroppedBody() {
		const body = new ReadableStream({
			pull(controller) {
				controller.error(new TypeError('Failed to fetch'));
			}
		});
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response(body)));
	}

	async function rejection(promise: Promise<unknown>): Promise<unknown> {
		return promise.then(
			() => undefined,
			(error: unknown) => error
		);
	}

	it('counts a connection dropped while the body was read', async () => {
		stubDroppedBody();
		const response = await fetchRecordingConnectionFailures('https://api.test/');
		expect(isConnectionFailure(await rejection(response.text()))).toBe(true);
	});

	it('does not count reading the same body twice, which is our bug', async () => {
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response('{}')));
		const response = await fetchRecordingConnectionFailures('https://api.test/');
		await response.text();
		const error = await rejection(response.text());
		expect(error).toBeInstanceOf(TypeError);
		expect(isConnectionFailure(error)).toBe(false);
	});

	it('does not count a body that is not valid JSON', async () => {
		vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response('<html>')));
		const response = await fetchRecordingConnectionFailures('https://api.test/');
		const error = await rejection(response.json());
		expect(error).toBeInstanceOf(SyntaxError);
		expect(isConnectionFailure(error)).toBe(false);
	});

	it('times out a request that never answers, as a connection failure', async () => {
		vi.useFakeTimers();
		// The native timeout runs on Node's own timer, which fake timers don't reach.
		vi.spyOn(AbortSignal, 'timeout').mockImplementation((ms) => {
			const controller = new AbortController();
			setTimeout(() => controller.abort(new DOMException('signal timed out', 'TimeoutError')), ms);
			return controller.signal;
		});
		try {
			vi.stubGlobal(
				'fetch',
				vi.fn<typeof fetch>(
					(_input, init) =>
						new Promise((_resolve, reject) => {
							init?.signal?.addEventListener('abort', () => {
								reject(init.signal?.reason as DOMException);
							});
						})
				)
			);
			const pending = rejection(fetchRecordingConnectionFailures(new Request('https://api.test/')));
			await vi.advanceTimersByTimeAsync(15_000);
			expect(isConnectionFailure(await pending)).toBe(true);
		} finally {
			vi.useRealTimers();
			vi.restoreAllMocks();
		}
	});

	it("keeps the caller's abort, which is not a connection failure", async () => {
		const controller = new AbortController();
		vi.stubGlobal(
			'fetch',
			vi.fn<typeof fetch>(
				(_input, init) =>
					new Promise((_resolve, reject) => {
						init?.signal?.addEventListener('abort', () => {
							reject(init.signal?.reason as DOMException);
						});
					})
			)
		);
		const pending = rejection(
			fetchRecordingConnectionFailures(
				new Request('https://api.test/', { signal: controller.signal })
			)
		);
		controller.abort();
		const error = await pending;
		expect(error).toBeInstanceOf(DOMException);
		expect(isConnectionFailure(error)).toBe(false);
	});
});

describe('throwApiError', () => {
	function thrown(apiError: unknown): unknown {
		try {
			throwApiError(apiError, 'Не удалось загрузить');
		} catch (error) {
			return error;
		}
		return undefined;
	}

	it("keeps the problem's status, so a missing record is a 404 page", () => {
		expect(thrown({ code: 'USER_NOT_FOUND', status: 404 })).toMatchObject({
			status: 404,
			body: { code: 'USER_NOT_FOUND' }
		});
	});

	it('is a 500 with the fallback copy when no API answer came back', async () => {
		expect(thrown(await droppedConnectionError())).toMatchObject({
			status: 500,
			body: { message: CONNECTION_FAILED }
		});
		expect(thrown(new TypeError('bug'))).toMatchObject({
			status: 500,
			body: { message: 'Не удалось загрузить' }
		});
	});
});
