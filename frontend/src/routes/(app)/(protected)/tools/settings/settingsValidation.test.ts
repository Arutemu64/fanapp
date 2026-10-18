import { describe, expect, it } from 'vitest';

import { m } from '#lib/paraglide/messages.js';

import {
	checkAnnouncementTimeout,
	checkFestivalEnd,
	checkFestivalStart,
	checkQuestCancelWindow,
	checkQuestMaxAward,
	QUEST_CANCEL_WINDOW_LIMIT,
	QUEST_MAX_AWARD_LIMIT
} from './settingsValidation';

describe('festival dates', () => {
	it('requires a start', () => {
		expect(checkFestivalStart('')).toBe(m.settings_validation_start());
		expect(checkFestivalStart('2026-10-17T10:00')).toBe('');
	});

	it('requires an end after the start', () => {
		expect(checkFestivalEnd('2026-10-17T10:00', '')).toBe(m.settings_validation_end());
		expect(checkFestivalEnd('2026-10-17T10:00', '2026-10-17T10:00')).toBe(
			m.error_invalid_festival_time_range()
		);
		expect(checkFestivalEnd('2026-10-17T10:00', '2026-10-17T09:59')).toBe(
			m.error_invalid_festival_time_range()
		);
		expect(checkFestivalEnd('2026-10-17T10:00', '2026-10-17T20:00')).toBe('');
	});

	it('leaves the range to the start rule while the start is empty', () => {
		expect(checkFestivalEnd('', '2026-10-17T20:00')).toBe('');
	});
});

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

describe('quest limits', () => {
	it('bounds the largest award to 1…limit', () => {
		expect(checkQuestMaxAward(1)).toBe('');
		expect(checkQuestMaxAward(QUEST_MAX_AWARD_LIMIT)).toBe('');
		expect(checkQuestMaxAward(0)).toBe(m.settings_validation_quest_max());
		expect(checkQuestMaxAward(QUEST_MAX_AWARD_LIMIT + 1)).toBe(m.settings_validation_quest_max());
		expect(checkQuestMaxAward(undefined)).toBe(m.settings_validation_quest_max());
	});

	it('bounds the cancel window to 0…limit', () => {
		expect(checkQuestCancelWindow(0)).toBe('');
		expect(checkQuestCancelWindow(QUEST_CANCEL_WINDOW_LIMIT)).toBe('');
		expect(checkQuestCancelWindow(-1)).toBe(m.settings_validation_quest_window());
		expect(checkQuestCancelWindow(2.5)).toBe(m.settings_validation_quest_window());
	});
});
