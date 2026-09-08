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
// use the function form to branch on query params or assert on the request body.
export type MockHandler = MockResponse | ((route: Route) => MockResponse | Promise<MockResponse>);

export type Handlers = Partial<Record<RouteKey, MockHandler>>;

/** Typed 200-by-default JSON response, so `json<Schema>(…)` checks the shape. */
export function json<T>(value: T, status = 200): MockResponse {
	return { status, json: value };
}

/**
 * Installs a single catch-all route over every `/api` request, backed by a
 * registry of per-endpoint handlers. Tests start from a baseline and narrow it
 * with `.use()`;
 * an endpoint nobody mocked returns a loud 404 and is recorded in `unmatched`, so
 * a forgotten mock fails the test instead of hanging on a doomed request.
 */
export class ApiMock {
	readonly unmatched: string[] = [];
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

	async install(): Promise<void> {
		await this.context.route('**/api/**', async (route) => {
			const request = route.request();
			const { pathname } = new URL(request.url());
			const key = `${request.method()} ${pathname.replace(/^\/api/, '')}` as RouteKey;

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
			return route.fulfill({
				status: response.status ?? 200,
				contentType: response.contentType ?? 'application/json',
				body: response.body ?? JSON.stringify(response.json ?? {})
			});
		});
	}
}
