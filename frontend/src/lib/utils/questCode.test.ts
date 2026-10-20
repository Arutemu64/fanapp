import { describe, expect, it } from 'vitest';

import { parseQuestCode, questCodeFor } from './questCode';

const USER_NUMBER = 482913;

describe('quest code', () => {
	it('round-trips a user number', () => {
		expect(parseQuestCode(questCodeFor(USER_NUMBER))).toBe(USER_NUMBER);
	});

	it('accepts surrounding whitespace and lower case', () => {
		expect(parseQuestCode(`  fanfan:${USER_NUMBER}\n`)).toBe(USER_NUMBER);
	});

	it.each([
		['a ticket barcode', '1234567890123'],
		['a website', 'https://example.com'],
		['a bare number', String(USER_NUMBER)],
		['a short number', 'FANFAN:48291'],
		['a leading zero', 'FANFAN:048291'],
		['a user ID', 'FANFAN:01890a5d-ac96-774b-bcce-b302099a8057']
	])('rejects %s', (_label, text) => {
		expect(parseQuestCode(text)).toBeNull();
	});
});
