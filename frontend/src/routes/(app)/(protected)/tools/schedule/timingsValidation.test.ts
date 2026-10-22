import { describe, expect, it } from 'vitest';

import { m } from '#lib/paraglide/messages.js';

import {
	CHANGEOVER_SECONDS_LIMIT,
	checkAnnouncementTimeout,
	checkChangeover
} from './timingsValidation';

describe('announcement timeout', () => {
	it.each([undefined, Number.NaN])('requires a value (%s)', (value) => {
		expect(checkAnnouncementTimeout(value)).toBe(m.settings_validation_timeout_required());
	});

	it.each([0, -1, 1.5])('rejects %s', (value) => {
		expect(checkAnnouncementTimeout(value)).toBe(m.settings_validation_timeout_integer());
	});

	it('accepts a positive whole number', () => {
		expect(checkAnnouncementTimeout(1)).toBe('');
	});
});

describe('changeover', () => {
	it.each([undefined, -1, 1.5, CHANGEOVER_SECONDS_LIMIT + 1])('rejects %s', (value) => {
		expect(checkChangeover(value)).toBe(m.settings_validation_changeover());
	});

	it.each([0, CHANGEOVER_SECONDS_LIMIT])('accepts %s', (value) => {
		expect(checkChangeover(value)).toBe('');
	});
});
