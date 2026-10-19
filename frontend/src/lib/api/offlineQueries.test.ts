import { describe, expect, it } from 'vitest';

import { responseSchemaHashes } from './generated/responseSchemaHashes.gen';
import { OFFLINE_QUERY_KEYS, operationIdOf } from './offlineQueries';

describe('OFFLINE_QUERY_KEYS', () => {
	// The persister drops a saved query its build has no hash for, so a missing
	// one (the generator's camel-casing drifting from hey-api's) would silently
	// stop that screen working offline after every restart.
	it('has a response schema hash for every offline query', () => {
		for (const queryKey of OFFLINE_QUERY_KEYS) {
			expect(responseSchemaHashes[operationIdOf(queryKey)]).toMatch(/^[0-9a-f]{16}$/);
		}
	});
});
