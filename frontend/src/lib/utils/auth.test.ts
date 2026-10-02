import { describe, expect, it } from 'vitest';

import { sanitizeNextPath } from './auth';

describe('sanitizeNextPath', () => {
	it.each([
		['/program', '/program'],
		['/a?b=c#d', '/a?b=c#d'],
		['//evil.com', null],
		['/\\evil.com', null],
		['\\\\evil.com', null],
		['https://evil.com', null],
		['javascript:alert(1)', null],
		['program', null],
		['', null],
		[null, null]
	])('%j -> %j', (raw, expected) => {
		expect(sanitizeNextPath(raw)).toBe(expected);
	});
});
