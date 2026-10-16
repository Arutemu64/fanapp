import { describe, expect, it } from 'vitest';

import { parseQuestCode, questCodeFor } from './questCode';

const USER_ID = '01890a5d-ac96-774b-bcce-b302099a8057';

describe('quest code', () => {
	it('round-trips a user ID', () => {
		expect(parseQuestCode(questCodeFor(USER_ID))).toBe(USER_ID);
	});

	it('accepts surrounding whitespace and upper-case hex', () => {
		expect(parseQuestCode(`  fanfan:user:${USER_ID.toUpperCase()}\n`)).toBe(USER_ID);
	});

	it.each([
		['a ticket barcode', '1234567890123'],
		['a website', 'https://example.com'],
		['a bare UUID', USER_ID],
		['a malformed ID', 'fanfan:user:not-a-uuid']
	])('rejects %s', (_label, text) => {
		expect(parseQuestCode(text)).toBeNull();
	});
});
