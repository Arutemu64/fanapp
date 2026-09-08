import type { BrowserContext, Route } from '@playwright/test';

import type { components } from '../../src/lib/api/schema';

// Every request/response schema generated from the backend OpenAPI spec. Typing
// mock bodies against these means a mock that drifts from the real contract fails
// to compile — the same drift guard the repo already applies to schema.d.ts.
export type ApiSchemas = components['schemas'];

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

// A route key is `"<METHOD> <path>"`, where <path> is the API path WITHOUT the
// `/api` base and WITH the trailing slash exactly as the backend declares it —
// e.g. `"GET /me/"`, `"GET /voting/status"`. Copy them from the OpenAPI paths.
export type RouteKey = `${Method} ${string}`;

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
export type MockHandler =
	MockResponse | ((route: Route) => MockResponse | void | Promise<MockResponse | void>);

export type Handlers = Partial<Record<RouteKey, MockHandler>>;

/** Typed 200-by-default JSON response, so `json<Schema>(…)` checks the shape. */
export function json<T>(value: T, status = 200): MockResponse {
	return { status, json: value };
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
	#handlers: Handlers;

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
				return route.fulfill({
					status: 404,
					contentType: 'application/json',
					body: JSON.stringify({ code: 'not_found', message: `Unmocked API route: ${key}` })
				});
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
