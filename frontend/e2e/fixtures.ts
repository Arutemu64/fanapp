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
	api: ApiMock;
	consoleErrors: ConsoleGuard;
	makeAxeBuilder: () => AxeBuilder;
	expectAccessible: (options?: AccessibleOptions) => Promise<void>;
}

export const test = base.extend<Fixtures>({
	api: [
		async ({ context }, use) => {
			await installSseDouble(context);
			const api = new ApiMock(context, baselineHandlers);
			await api.install();
			await use(api);
			expect(api.unmatched, `Unmocked API routes:\n${api.unmatched.join('\n')}`).toEqual([]);
		},
		{ auto: true }
	],

	consoleErrors: [
		async ({ page }, use) => {
			const { guard, assertClean } = watchConsole(page);
			await use(guard);
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

export { json, problem } from './mocks/api';
export { loggedInAs, organizer } from './mocks/personas';
export { emitSse } from './mocks/sse';
export { expect } from '@playwright/test';
