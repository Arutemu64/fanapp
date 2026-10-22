import { m } from '#lib/paraglide/messages.js';

// Each check returns the field's error message, or '' when the value is valid.

// Mirror the backend bounds (UpdateQuestInput).
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

/** Both values are datetime-local strings, which compare correctly as text. */
export function checkFestivalEnd(start: string, end: string): string {
	if (!end) {
		return m.settings_validation_end();
	}
	// Guard the range: the backend stores the two instants independently with no
	// ordering check, and an end at or before the start collapses the home page's
	// "during" phase entirely — the countdown would jump straight to the farewell.
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
