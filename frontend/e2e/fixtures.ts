import { test as base } from '@playwright/test';

import { ApiMock } from './mocks/api';
import { baselineHandlers } from './mocks/defaults';
import { installSseDouble } from './mocks/sse';

export interface Fixtures {
	// The mocked backend, pre-loaded with the boot-critical endpoints for a guest.
	// Reference it in a test (`{ page, api }`) to log a user in or override a route
	// before navigating: `api.use(loggedInAs())` / `api.use({ 'GET /voting/status': … })`.
	api: ApiMock;
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
	}
});

export { json } from './mocks/api';
export { loggedInAs, organizer, user } from './mocks/personas';
export { emitSse } from './mocks/sse';
export { expect } from '@playwright/test';
