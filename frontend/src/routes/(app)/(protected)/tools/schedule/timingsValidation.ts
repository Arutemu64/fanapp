import { m } from '#lib/paraglide/messages.js';

export const CHANGEOVER_SECONDS_LIMIT = 600;

export function checkAnnouncementCooldown(value: number | undefined): string {
	if (value === undefined || Number.isNaN(value)) {
		return m.settings_validation_timeout_required();
	}
	if (!Number.isInteger(value) || value < 1) {
		return m.settings_validation_timeout_integer();
	}
	return '';
}

export function checkChangeover(value: number | undefined): string {
	if (value === undefined || !Number.isInteger(value)) {
		return m.settings_validation_changeover();
	}
	if (value < 0 || value > CHANGEOVER_SECONDS_LIMIT) {
		return m.settings_validation_changeover();
	}
	return '';
}
