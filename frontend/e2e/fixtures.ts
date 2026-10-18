import type AxeBuilder from '@axe-core/playwright';

import { test as base, expect } from '@playwright/test';

import type { AccessibleOptions } from './support/axe';
import type { ConsoleGuard } from './support/console';

import { ApiMock } from './mocks/api';
import { baselineHandlers } from './mocks/defaults';
import { installSseDouble } from './mocks/sse';
import { axeBuilder, expectAccessible } from './support/axe';
import { watchConsole } from './support/console';

export interface Fixtures {
	// The mocked backend, pre-loaded with the boot-critical endpoints for a guest.
	// Auto-installed on every test; reference it in a test (`{ page, api }`) to log a user in or override a route
	// before navigating: `api.use(loggedInAs())` / `api.use({ 'GET /voting/status': … })`.
	api: ApiMock;
	// Auto-installed on every test (no need to reference it): an unexpected browser
	// console error or uncaught exception fails the spec. Reference it only to
	// `allow(...)` an error a test deliberately provokes.
	consoleErrors: ConsoleGuard;
	// A WCAG-scoped AxeBuilder factory for the page under test. Narrow it with
	// `.include()` or relax a known issue with `.disableRules()`, then hand it to
	// `expectAccessible`.
	makeAxeBuilder: () => AxeBuilder;
	// Scan the page, attach the results to the report, and fail on violations or
	// on contrast axe couldn't decide: `await expectAccessible()`. Pass a narrowed
	// `builder`, or `contrastCheckedByHand` for text over a photo.
	expectAccessible: (options?: AccessibleOptions) => Promise<void>;
}

export const test = base.extend<Fixtures>({
	// `auto` because fixtures are otherwise lazy: a test that never names `api`
	// would get no mock and no SSE double, and talk to whatever backend is (not)
	// listening behind the preview proxy. https://playwright.dev/docs/test-fixtures
	api: [
		async ({ context }, use) => {
			// Both must be installed on the context BEFORE the test navigates, which the
			// test body always does — so the baseline covers the boot requests and the
			// app never opens a live SSE stream.
			await installSseDouble(context);
			const api = new ApiMock(context, baselineHandlers);
			await api.install();
			await use(api);
			// Teardown: an unmocked endpoint gets a 404 the app may swallow into an
			// empty or error state the test never looks at, so fail on it here
			// rather than trusting each spec to assert it.
			expect(api.unmatched, `Unmocked API routes:\n${api.unmatched.join('\n')}`).toEqual([]);
		},
		{ auto: true }
	],

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
	},

	expectAccessible: async ({ page }, use, testInfo) => {
		await use((options) => expectAccessible(page, testInfo, options));
	}
});

export { json } from './mocks/api';
export { loggedInAs, organizer } from './mocks/personas';
export { emitSse } from './mocks/sse';
export { expect } from '@playwright/test';
