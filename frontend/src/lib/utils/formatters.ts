import { PUBLIC_TIMEZONE } from '$env/static/public';

const SECONDS_IN_MINUTE = 60;
const SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE;

// Single event/venue timezone for the whole app. Everyone using this app is at
// the venue, so times are shown on the venue clock regardless of the device's own
// zone — this is an event timezone, not a per-user one. Sourced from
// PUBLIC_TIMEZONE so it stays in sync with the backend's TIMEZONE; falls back to
// the same Europe/Moscow default the backend uses when the build var is empty.
const EVENT_TIME_ZONE = PUBLIC_TIMEZONE || 'Europe/Moscow';

/**
 * Render an event's `duration`, which the API carries in **seconds** end to end
 * so a sub-minute act stays exact — the same value ADR-0008 projects expected
 * start times from, where rounding to whole minutes would accumulate as drift.
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
		parts.push(`${hours} ${pluralize(hours, 'час', 'часа', 'часов')}`);
	}
	if (minutes > 0) {
		parts.push(`${minutes} ${pluralize(minutes, 'минута', 'минуты', 'минут')}`);
	}
	// Also covers a zero duration, which would otherwise render as an empty label.
	if (remainingSeconds > 0 || parts.length === 0) {
		parts.push(
			`${remainingSeconds} ${pluralize(remainingSeconds, 'секунда', 'секунды', 'секунд')}`
		);
	}

	return parts.join(' ');
}

const EVENT_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: '2-digit',
	month: '2-digit',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	timeZone: EVENT_TIME_ZONE
});

function formatEventDateTime(value: string | number | Date): string {
	return EVENT_DATE_TIME_FORMATTER.format(new Date(value));
}

export function formatRelativeTime(value: string | number | Date): string {
	const date = new Date(value);
	const now = new Date();
	const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

	if (diffSeconds < 60) {
		return 'только что';
	}

	const diffMinutes = Math.floor(diffSeconds / 60);
	if (diffMinutes < 60) {
		return `${diffMinutes} ${pluralize(diffMinutes, 'минуту', 'минуты', 'минут')} назад`;
	}

	const diffHours = Math.floor(diffMinutes / 60);
	if (diffHours < 24) {
		return `${diffHours} ${pluralize(diffHours, 'час', 'часа', 'часов')} назад`;
	}

	return formatEventDateTime(date);
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
		return `сегодня в ${time}`;
	}
	if (targetDay === EVENT_DAY_KEY_FORMATTER.format(yesterday)) {
		return `вчера в ${time}`;
	}
	return `${EVENT_DAY_MONTH_FORMATTER.format(target)} в ${time}`;
}

/**
 * Relative countdown to an event's projected start, e.g. "через 2 часа 15 минут".
 * Spelled out (not abbreviated) to match {@link formatDuration} on the same row.
 *
 * `now` is passed in rather than read here so the label is pure/testable and
 * re-derives when the caller does — on each schedule reload (one per set-current
 * SSE, at most a sub-5-minute act apart), which is what keeps a static countdown
 * from drifting far. A projected start already in the past means the snapshot
 * drifted since that reload, so the countdown would be visibly wrong: it is
 * dropped and the drift-proof queue distance stands alone.
 */
function formatStartsIn(expectedStartTime: string, now: number): string {
	const diffMs = new Date(expectedStartTime).getTime() - now;
	if (diffMs <= 0) {
		return '';
	}

	const totalMinutes = Math.floor(diffMs / (SECONDS_IN_MINUTE * 1000));
	if (totalMinutes < 1) {
		return 'меньше минуты';
	}

	const hours = Math.floor(totalMinutes / 60);
	const minutes = totalMinutes % 60;

	const parts: string[] = [];
	if (hours > 0) {
		parts.push(`${hours} ${pluralize(hours, 'час', 'часа', 'часов')}`);
	}
	if (minutes > 0) {
		// Accusative forms ("через 1 минуту", not "1 минута"): the preposition
		// "через" governs the accusative, unlike the caseless formatDuration label.
		parts.push(`${minutes} ${pluralize(minutes, 'минуту', 'минуты', 'минут')}`);
	}

	return `через ${parts.join(' ')}`;
}

/**
 * Countdown label for an upcoming event: the drift-proof queue distance ("how
 * many acts away") plus a relative countdown to its projected start. On a
 * schedule that drifts, the queue distance is always exact; the countdown is
 * re-derived on each schedule reload rather than ticking (see
 * {@link formatStartsIn}). See ADR-0008.
 */
export function formatUntil(
	queueUntil: number,
	expectedStartTime: string | null,
	now: number
): string {
	const base = `Осталось ${queueUntil} ${pluralize(queueUntil, 'выступление', 'выступления', 'выступлений')}`;
	if (!expectedStartTime) {
		return base;
	}

	const startsIn = formatStartsIn(expectedStartTime, now);
	return startsIn ? `${base} · ${startsIn}` : base;
}

/**
 * Pluralize a Russian word based on count
 * @param count - The number
 * @param one - Form for 1 (e.g., "событие")
 * @param few - Form for 2-4 (e.g., "события")
 * @param many - Form for 5+ (e.g., "событий")
 */
export function pluralize(count: number, one: string, few: string, many: string): string {
	const mod10 = count % 10;
	const mod100 = count % 100;
	if (mod10 === 1 && mod100 !== 11) return one;
	if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
	return many;
}
