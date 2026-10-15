import { PUBLIC_TIMEZONE } from '$app/env/public';

import { m } from '#lib/paraglide/messages.js';

const SECONDS_IN_MINUTE = 60;
const SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE;

// Single event/venue timezone for the whole app. Everyone using this app is at
// the venue, so times are shown on the venue clock regardless of the device's own
// zone — this is an event timezone, not a per-user one. Sourced from
// PUBLIC_TIMEZONE so it stays in sync with the backend's TIMEZONE; falls back to
// the same Europe/Moscow default the backend uses when the build var is empty.
const EVENT_TIME_ZONE = PUBLIC_TIMEZONE || 'Europe/Moscow';

/**
 * An act's public number as people see it in the programme: "7" reads as "007".
 * Null for numberless rows (breaks and other filler), which render no badge.
 */
export function formatEventNumber(number: number | null | undefined): string | null {
	if (number === null || number === undefined) return null;
	return String(number).padStart(3, '0');
}

/**
 * Render an event's `duration`, which the API carries in **seconds** end to end
 * so a sub-minute act stays exact and rounding to whole minutes cannot accumulate
 * error across the programme.
 *
 * Units are dropped when they are zero, so a whole-minute act still reads
 * "15 минут" rather than "15 минут 0 секунд".
 */
export function formatDuration(seconds: number): string {
	// Guards a negative or fractional value from the API into something
	// renderable; the label is a read-only meta line, not a place to surface it.
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
	// Also covers a zero duration, which would otherwise render as an empty label.
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

/** Festival day on the venue clock, weekday last: "13 марта 2027, суббота". */
export function formatFestivalDate(value: string | number | Date): string {
	const parts = FESTIVAL_DATE_FORMATTER.formatToParts(new Date(value));
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((part) => part.type === type)?.value ?? '';
	return `${get('day')} ${get('month')} ${get('year')}, ${get('weekday')}`;
}

/** Wall-clock time on the venue clock: "11:30". */
export function formatFestivalTime(value: string | number | Date): string {
	return FESTIVAL_TIME_FORMATTER.format(new Date(value));
}

/**
 * Festival start for the hero, on the venue clock: "13 марта 2027, 11:30".
 * Built from parts so it drops the " г." year suffix ru-RU's long format adds,
 * matching the app's existing date copy.
 */
export function formatFestivalDateTime(value: string | number | Date): string {
	const parts = FESTIVAL_DATE_TIME_FORMATTER.formatToParts(new Date(value));
	const get = (type: Intl.DateTimeFormatPartTypes) =>
		parts.find((part) => part.type === type)?.value ?? '';
	return `${get('day')} ${get('month')} ${get('year')}, ${get('hour')}:${get('minute')}`;
}

// Wall-clock parts in the event timezone, used to convert to/from the zone-naive
// <input type="datetime-local"> value organizers edit festival_start with.
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

/**
 * Minutes the event timezone is ahead of UTC at `date`. Derived via Intl so it
 * follows the zone's real rules rather than a hardcoded +03:00 that would break
 * if PUBLIC_TIMEZONE moved to a DST zone.
 */
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

/**
 * ISO instant → "YYYY-MM-DDTHH:mm" on the venue clock, to populate a
 * <input type="datetime-local"> (which is zone-naive).
 */
export function toEventDateTimeLocal(iso: string): string {
	const p = eventWallClockParts(new Date(iso));
	return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

/**
 * "YYYY-MM-DDTHH:mm" venue-clock value from a datetime-local input → ISO instant
 * for the API. Reads the input as UTC first, then shifts by the zone's offset at
 * that wall clock. Exact for the venue's fixed-offset zone; at a DST boundary the
 * one ambiguous hour could land an hour off, which festival_start never needs.
 */
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

/**
 * "5 минут назад" for the last day, the venue-clock date and time after that.
 * `now` is injectable so a caller can re-render against a ticking clock (see
 * `minuteClock`) instead of freezing the label at first render.
 */
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

// Y-M-D in the event timezone, used only to compare calendar days regardless of
// the device's own timezone (en-CA gives a stable "2026-06-19" shape).
const EVENT_DAY_KEY_FORMATTER = new Intl.DateTimeFormat('en-CA', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

/**
 * Format when cached data was last synced, for the offline stale notice. Caching
 * may have happened days earlier (installed at home, opened at the venue), so the
 * day is always shown unless it is today/yesterday. Event timezone, like the rest
 * of the app.
 */
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

/**
 * The venue-clock calendar day of an instant, as "YYYY-MM-DD" — a grouping key
 * that ignores the device's own timezone.
 */
export function eventDayKey(value: string | number | Date): string {
	return EVENT_DAY_KEY_FORMATTER.format(new Date(value));
}

/**
 * The "YYYY-MM-DD" key of the calendar day before `dayKey`. Plain date
 * arithmetic, not "now minus 24 hours": across a DST switch in the venue zone a
 * day is 23 or 25 hours long, and the subtraction would land on the wrong date.
 */
export function previousDayKey(dayKey: string): string {
	const year = Number(dayKey.slice(0, 4));
	const month = Number(dayKey.slice(5, 7));
	const day = Number(dayKey.slice(8, 10));
	return new Date(Date.UTC(year, month - 1, day - 1)).toISOString().slice(0, 10);
}

/**
 * Day heading for a date-grouped feed: "Сегодня", "Вчера", else "8 октября"
 * (with the year only when it isn't the current one). Venue clock.
 */
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
	// ru-RU appends " г." to a long date with a year; the app's date copy drops it.
	return EVENT_DAY_LONG_WITH_YEAR_FORMATTER.format(target).replace(/\s*г\.$/, '');
}

/**
 * Countdown label for an upcoming event: the drift-proof position distance ("how
 * many acts away"). The schedule carries no predicted clock time — every value
 * is derived purely from stored columns so the payload stays cacheable (ADR-0014)
 * — so the position distance is the whole label, and it stays exact as acts advance.
 */
export function formatUntil(actsAhead: number): string {
	return m.events_left({ count: actsAhead });
}
