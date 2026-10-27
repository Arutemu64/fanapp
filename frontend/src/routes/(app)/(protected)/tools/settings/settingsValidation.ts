import { m } from '#lib/paraglide/messages.js';

export const QUEST_MAX_AWARD_LIMIT = 10_000;
export const QUEST_CANCEL_WINDOW_LIMIT = 1440;

function isIntegerInRange(value: number | undefined, min: number, max: number): boolean {
	return value !== undefined && Number.isInteger(value) && value >= min && value <= max;
}

export function checkFestivalStart(start: string): string {
	if (!start) {
		return m.settings_validation_start();
	}
	return '';
}

export function checkFestivalEnd(start: string, end: string): string {
	if (!end) {
		return m.settings_validation_end();
	}
	if (start && end <= start) {
		return m.error_invalid_festival_time_range();
	}
	return '';
}

export function checkQuestMaxAward(value: number | undefined): string {
	if (isIntegerInRange(value, 1, QUEST_MAX_AWARD_LIMIT)) {
		return '';
	}
	return m.settings_validation_quest_max();
}

export function checkQuestCancelWindow(value: number | undefined): string {
	if (isIntegerInRange(value, 0, QUEST_CANCEL_WINDOW_LIMIT)) {
		return '';
	}
	return m.settings_validation_quest_window();
}
