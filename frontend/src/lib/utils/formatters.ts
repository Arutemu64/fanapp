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

const FESTIVAL_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: 'numeric',
	month: 'long',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	hourCycle: 'h23',
	timeZone: EVENT_TIME_ZONE
});

/**
 * Festival start for the hero, on the venue clock: "22 августа 2026, 11:30".
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
 * Countdown label for an upcoming event: the drift-proof queue distance ("how
 * many acts away"). The schedule carries no predicted clock time — every value
 * is derived purely from stored columns so the payload stays cacheable (ADR-0014)
 * — so the queue distance is the whole label, and it stays exact as acts advance.
 */
export function formatUntil(queueUntil: number): string {
	return `Осталось ${queueUntil} ${pluralize(queueUntil, 'выступление', 'выступления', 'выступлений')}`;
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
