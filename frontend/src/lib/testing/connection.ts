import { vi } from 'vitest';

import { fetchRecordingConnectionFailures } from '#lib/api/errors.js';

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
