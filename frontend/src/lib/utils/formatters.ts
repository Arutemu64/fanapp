import { PUBLIC_TIMEZONE } from '$app/env/public';

import { m } from '#lib/paraglide/messages.js';

const SECONDS_IN_MINUTE = 60;
const SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE;

const EVENT_TIME_ZONE = PUBLIC_TIMEZONE || 'Europe/Moscow';

export function formatEventNumber(number: number | null | undefined): string | null {
	if (number === null || number === undefined) return null;
	return String(number).padStart(3, '0');
}

export function formatDuration(seconds: number): string {
	const total = Math.max(0, Math.round(seconds));

	const hours = Math.floor(total / SECONDS_IN_HOUR);
	const minutes = Math.floor((total % SECONDS_IN_HOUR) / SECONDS_IN_MINUTE);
	const remainingSeconds = total % SECONDS_IN_MINUTE;

	const parts: string[] = [];
	if (hours > 0) {
		parts.push(m.duration_hours({ count: hours }));
	}
	if (minutes > 0) {
		parts.push(m.duration_minutes({ count: minutes }));
	}
	if (remainingSeconds > 0 || parts.length === 0) {
		parts.push(m.duration_seconds({ count: remainingSeconds }));
	}

	return parts.join(' ');
}

const FESTIVAL_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: 'numeric',
	month: 'long',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	hourCycle: 'h23',
	timeZone: EVENT_TIME_ZONE
});

const FESTIVAL_DATE_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	weekday: 'long',
	day: 'numeric',
	month: 'long',
	year: 'numeric',
	timeZone: EVENT_TIME_ZONE
});

const FESTIVAL_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	hour: '2-digit',
	minute: '2-digit',
	hourCycle: 'h23',
	timeZone: EVENT_TIME_ZONE
});

export function formatFestivalDate(value: string | number | Date): string {
	const parts = FESTIVAL_DATE_FORMATTER.formatToParts(new Date(value));
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((part) => part.type === type)?.value ?? '';
	return `${get('day')} ${get('month')} ${get('year')}, ${get('weekday')}`;
}

export function formatFestivalTime(value: string | number | Date): string {
	return FESTIVAL_TIME_FORMATTER.format(new Date(value));
}

export function formatFestivalDateTime(value: string | number | Date): string {
	const parts = FESTIVAL_DATE_TIME_FORMATTER.formatToParts(new Date(value));
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((part) => part.type === type)?.value ?? '';
	return `${get('day')} ${get('month')} ${get('year')}, ${get('hour')}:${get('minute')}`;
}

const EVENT_WALL_CLOCK_FORMATTER = new Intl.DateTimeFormat('en-CA', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	hour: '2-digit',
	minute: '2-digit',
	second: '2-digit',
	hourCycle: 'h23',
	timeZone: EVENT_TIME_ZONE
});

function eventWallClockParts(date: Date): Record<string, string> {
	const parts: Record<string, string> = {};
	for (const part of EVENT_WALL_CLOCK_FORMATTER.formatToParts(date)) {
		parts[part.type] = part.value;
	}
	return parts;
}

function eventZoneOffsetMinutes(date: Date): number {
	const p = eventWallClockParts(date);
	const asUtc = Date.UTC(
		Number(p.year),
		Number(p.month) - 1,
		Number(p.day),
		Number(p.hour),
		Number(p.minute),
		Number(p.second)
	);
	return (asUtc - date.getTime()) / 60_000;
}

export function toEventDateTimeLocal(iso: string): string {
	const p = eventWallClockParts(new Date(iso));
	return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

export function fromEventDateTimeLocal(value: string): string {
	const naiveUtc = new Date(`${value}:00Z`).getTime();
	const offsetMs = eventZoneOffsetMinutes(new Date(naiveUtc)) * 60_000;
	return new Date(naiveUtc - offsetMs).toISOString();
}

const EVENT_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: '2-digit',
	month: '2-digit',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

export function formatRelativeTime(
	value: string | number | Date,
	now: number = Date.now()
): string {
	const date = new Date(value);
	const diffSeconds = Math.floor((now - date.getTime()) / 1000);

	if (diffSeconds < 60) {
		return m.relative_just_now();
	}

	const diffMinutes = Math.floor(diffSeconds / 60);
	if (diffMinutes < 60) {
		return m.relative_minutes_ago({ count: diffMinutes });
	}

	const diffHours = Math.floor(diffMinutes / 60);
	if (diffHours < 24) {
		return m.relative_hours_ago({ count: diffHours });
	}

	return EVENT_DATE_TIME_FORMATTER.format(date);
}

const EVENT_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	hour: '2-digit',
	minute: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

const EVENT_DAY_MONTH_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: '2-digit',
	month: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

const EVENT_DAY_KEY_FORMATTER = new Intl.DateTimeFormat('en-CA', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

export function formatSyncedAt(timestamp: number): string {
	const target = new Date(timestamp);
	const time = EVENT_TIME_FORMATTER.format(target);

	const now = new Date();
	const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
	const targetDay = EVENT_DAY_KEY_FORMATTER.format(target);

	if (targetDay === EVENT_DAY_KEY_FORMATTER.format(now)) {
		return m.synced_today({ time });
	}
	if (targetDay === EVENT_DAY_KEY_FORMATTER.format(yesterday)) {
		return m.synced_yesterday({ time });
	}
	return m.synced_on_date({ date: EVENT_DAY_MONTH_FORMATTER.format(target), time });
}

const EVENT_DAY_LONG_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: 'numeric',
	month: 'long',
	timeZone: EVENT_TIME_ZONE
});

const EVENT_DAY_LONG_WITH_YEAR_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: 'numeric',
	month: 'long',
	year: 'numeric',
	timeZone: EVENT_TIME_ZONE
});

export function eventDayKey(value: string | number | Date): string {
	return EVENT_DAY_KEY_FORMATTER.format(new Date(value));
}

export function previousDayKey(dayKey: string): string {
	const year = Number(dayKey.slice(0, 4));
	const month = Number(dayKey.slice(5, 7));
	const day = Number(dayKey.slice(8, 10));
	return new Date(Date.UTC(year, month - 1, day - 1)).toISOString().slice(0, 10);
}

export function formatDayHeading(value: string | number | Date, now: number = Date.now()): string {
	const target = new Date(value);
	const targetDay = eventDayKey(target);

	if (targetDay === eventDayKey(now)) {
		return m.day_today();
	}
	if (targetDay === previousDayKey(eventDayKey(now))) {
		return m.day_yesterday();
	}

	const sameYear = targetDay.slice(0, 4) === eventDayKey(now).slice(0, 4);
	if (sameYear) {
		return EVENT_DAY_LONG_FORMATTER.format(target);
	}
	return EVENT_DAY_LONG_WITH_YEAR_FORMATTER.format(target).replace(/\s*г\.$/, '');
}

const UNTIL_ROUNDING_FROM_SECONDS = 10 * SECONDS_IN_MINUTE;
const UNTIL_ROUNDING_STEP_SECONDS = 5 * SECONDS_IN_MINUTE;

export function formatUntil(actsAhead: number, secondsAhead: number): string {
	if (secondsAhead <= 0) {
		return m.events_left({ count: actsAhead });
	}
	let rounded = Math.ceil(secondsAhead / SECONDS_IN_MINUTE) * SECONDS_IN_MINUTE;
	if (rounded >= UNTIL_ROUNDING_FROM_SECONDS) {
		rounded = Math.ceil(rounded / UNTIL_ROUNDING_STEP_SECONDS) * UNTIL_ROUNDING_STEP_SECONDS;
	}
	return m.events_left_time({ time: formatDuration(rounded) });
}
