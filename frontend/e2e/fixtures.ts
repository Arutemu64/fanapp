import type AxeBuilder from '@axe-core/playwright';

import { test as base } from '@playwright/test';

import type { ConsoleGuard } from './support/console';

import { ApiMock } from './mocks/api';
import { baselineHandlers } from './mocks/defaults';
import { installSseDouble } from './mocks/sse';
import { axeBuilder } from './support/axe';
import { watchConsole } from './support/console';

export interface Fixtures {
	// The mocked backend, pre-loaded with the boot-critical endpoints for a guest.
	// Reference it in a test (`{ page, api }`) to log a user in or override a route
	// before navigating: `api.use(loggedInAs())` / `api.use({ 'GET /voting/status': … })`.
	api: ApiMock;
	// Auto-installed on every test (no need to reference it): an unexpected browser
	// console error or uncaught exception fails the spec. Reference it only to
	// `allow(...)` an error a test deliberately provokes.
	consoleErrors: ConsoleGuard;
	// A WCAG-scoped AxeBuilder factory for the page under test. `await
	// makeAxeBuilder().analyze()` and assert `results.violations` is empty; narrow
	// with `.include()` or relax a known issue with `.disableRules()`.
	makeAxeBuilder: () => AxeBuilder;
}

export const test = base.extend<Fixtures>({
	api: async ({ context }, use) => {
		// Both must be installed on the context BEFORE the test navigates, which the
		// test body always does — so the baseline covers the boot requests and the
		// app never opens a live SSE stream.
		await installSseDouble(context);
		const api = new ApiMock(context, baselineHandlers);
		await api.install();
		await use(api);
	},

	consoleErrors: [
		async ({ page }, use) => {
			const { guard, assertClean } = watchConsole(page);
			await use(guard);
			// Teardown, after the test body: fail if the page logged an error nobody
			// allowed. Runs for every test because the fixture is `auto`.
			assertClean();
		},
		{ auto: true }
	],

	makeAxeBuilder: async ({ page }, use) => {
		await use(() => axeBuilder(page));
	}
});

export type { ApiSchemas } from './mocks/api';
export { json } from './mocks/api';
export { loggedInAs, organizer, user } from './mocks/personas';
export { emitSse } from './mocks/sse';
export { expect } from '@playwright/test';
