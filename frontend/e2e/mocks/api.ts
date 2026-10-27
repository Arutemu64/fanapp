import type { BrowserContext, Route } from '@playwright/test';

import { STATUS_CODES } from 'node:http';

import type openapi from '../../../shared/openapi/openapi.json';
import type { ProblemDetails } from '../../src/lib/api/generated/types.gen';

type Paths = (typeof openapi)['paths'];
type Path = Extract<keyof Paths, string>;
type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete';

type Concrete<P extends string> = P extends `${infer Head}{${string}}${infer Tail}`
	? `${Head}${string}${Concrete<Tail>}`
	: P;

export type RouteKey = {
	[P in Path]: `${Uppercase<Extract<keyof Paths[P], HttpMethod>>} ${Concrete<P>}`;
}[Path];

export interface MockResponse {
	status?: number;
	json?: unknown;
	body?: string;
	contentType?: string;
}

/* eslint-disable @typescript-eslint/no-invalid-void-type -- an async handler that fulfils the route itself resolves to void, which `undefined` rejects */
type MockHandler =
	MockResponse | ((route: Route) => MockResponse | void | Promise<MockResponse | void>);
/* eslint-enable @typescript-eslint/no-invalid-void-type */

export type Handlers = Partial<Record<RouteKey, MockHandler>>;

// eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters -- callers pass T explicitly to type-check the literal
export function json<T>(value: T, status = 200): MockResponse {
	return { status, json: value };
}

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

	use(handlers: Handlers): this {
		Object.assign(this.#handlers, handlers);
		return this;
	}

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
			if (response === undefined) return;
			return route.fulfill({
				status: response.status ?? 200,
				contentType: response.contentType ?? 'application/json',
				body: response.body ?? JSON.stringify(response.json ?? {})
			});
		});
	}
}
