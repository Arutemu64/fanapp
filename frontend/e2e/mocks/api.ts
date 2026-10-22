import type { BrowserContext, Route } from '@playwright/test';

import { STATUS_CODES } from 'node:http';

import type openapi from '../../../shared/openapi/openapi.json';
import type { ProblemDetails } from '../../src/lib/api/generated/types.gen';

type Paths = (typeof openapi)['paths'];
type Path = Extract<keyof Paths, string>;
type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete';

// `/users/{user_id}` becomes `/users/${string}`, so a test names the concrete
// id it mocks and still type-checks.
type Concrete<P extends string> = P extends `${infer Head}{${string}}${infer Tail}`
	? `${Head}${string}${Concrete<Tail>}`
	: P;

// A route key is `"<METHOD> <path>"`, where <path> is the API path WITHOUT the
// `/api` base and WITH the trailing slash exactly as the backend declares it —
// e.g. `"GET /me"`, `"GET /voting/status"`. The union is derived from the
// committed OpenAPI spec, so a typo or a route the backend dropped fails to
// compile instead of failing at runtime as an unmocked 404.
export type RouteKey = {
	[P in Path]: `${Uppercase<Extract<keyof Paths[P], HttpMethod>>} ${Concrete<P>}`;
}[Path];

export interface MockResponse {
	status?: number;
	json?: unknown;
	body?: string;
	contentType?: string;
}

// A handler is either a fixed response or a function of the intercepted request —
// use the function form to branch on query params, assert on the request body, or
// take the route over entirely (e.g. `route.abort()` to simulate a dead network,
// which is how the mocked tier drives the app's offline states). A function that
// fulfils/aborts the route itself returns nothing.
/* eslint-disable @typescript-eslint/no-invalid-void-type -- an async handler that fulfils the route itself resolves to void, which `undefined` rejects */
type MockHandler =
	MockResponse | ((route: Route) => MockResponse | void | Promise<MockResponse | void>);
/* eslint-enable @typescript-eslint/no-invalid-void-type */

export type Handlers = Partial<Record<RouteKey, MockHandler>>;

/** Typed 200-by-default JSON response, so `json<Schema>(…)` checks the shape. */
// eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters -- callers pass T explicitly to type-check the literal
export function json<T>(value: T, status = 200): MockResponse {
	return { status, json: value };
}

/**
 * An error response shaped like the backend's (RFC 9457 problem details, see
 * `problem_response()`): `type` derived from `code`, `title` the status phrase,
 * extension members beside them. `code` is typed against the spec's enum, so a
 * mock can't use a code the API never sends.
 */
export function problem(
	code: ProblemDetails['code'],
	status: number,
	extensions: Record<string, unknown> = {}
): MockResponse {
	return {
		status,
		contentType: 'application/problem+json',
		body: JSON.stringify({
			...extensions,
			type: `/problems/${code.toLowerCase().replaceAll('_', '-')}`,
			title: STATUS_CODES[status],
			status,
			code
		})
	};
}

/**
 * Installs a single catch-all route over every `/api` request, backed by a
 * registry of per-endpoint handlers. Tests start from a baseline and narrow it
 * with `.use()`; an endpoint nobody mocked returns a loud 404 and is recorded in
 * `unmatched`, so a forgotten mock fails the test instead of hanging on a doomed
 * request. Every matched request is recorded in `calls` (see `countCalls`), which
 * lets a test assert that, say, an SSE event triggered a refetch.
 */
export class ApiMock {
	readonly unmatched: string[] = [];
	readonly calls: string[] = [];
	readonly #handlers: Handlers;

	constructor(
		private readonly context: BrowserContext,
		baseline: Handlers
	) {
		this.#handlers = { ...baseline };
	}

	/** Add or override handlers for the current test. Last write wins. */
	use(handlers: Handlers): this {
		Object.assign(this.#handlers, handlers);
		return this;
	}

	/** How many times a route was requested — for asserting refetches. */
	countCalls(key: RouteKey): number {
		return this.calls.filter((call) => call === key).length;
	}

	async install(): Promise<void> {
		await this.context.route('**/api/**', async (route) => {
			const request = route.request();
			const { pathname } = new URL(request.url());
			const key = `${request.method()} ${pathname.replace(/^\/api/, '')}` as RouteKey;

			this.calls.push(key);

			const handler = this.#handlers[key];
			if (handler === undefined) {
				this.unmatched.push(key);
				return route.fulfill(problem('HTTP_ERROR', 404, { unmocked: key }));
			}

			const response = typeof handler === 'function' ? await handler(route) : handler;
			// A function handler that fulfilled or aborted the route itself returns
			// nothing — there is no response left for us to send.
			if (response === undefined) return;
			return route.fulfill({
				status: response.status ?? 200,
				contentType: response.contentType ?? 'application/json',
				body: response.body ?? JSON.stringify(response.json ?? {})
			});
		});
	}
}
