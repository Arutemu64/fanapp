import { vi } from 'vitest';

import { fetchRecordingConnectionFailures } from '#lib/api/errors.js';

/**
 * The TypeError a dropped connection produces, as the API client sees it:
 * rejected by `fetch` itself, so `isConnectionFailure` recognises it. A bare
 * `new TypeError()` reads as a bug in our own code instead.
 */
export async function droppedConnectionError(): Promise<unknown> {
	vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch')));
	try {
		return await fetchRecordingConnectionFailures('https://api.test/').then(
			() => undefined,
			(error: unknown) => error
		);
	} finally {
		vi.unstubAllGlobals();
	}
}
