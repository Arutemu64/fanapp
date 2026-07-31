const SECONDS_PER_MINUTE = 60;
const SECONDS_PER_HOUR = 3600;

/**
 * How long an act runs, in Russian. Acts span a ~30-second single defile to a
 * 20-minute closing ceremony, so seconds have to survive the formatting: the
 * previous version rounded everything up to whole minutes, which rendered every
 * short act as "1 минута", and its `% 3600` silently dropped whole hours.
 *
 * A single unit gets the full word; a compound is abbreviated ("1 мин 30 с")
 * because "1 минута 30 секунд" does not fit the meta row on a phone.
 */
export function formatDuration(seconds: number): string {
	if (seconds < SECONDS_PER_MINUTE) {
		return `${seconds} ${pluralize(seconds, 'секунда', 'секунды', 'секунд')}`;
	}

	if (seconds < SECONDS_PER_HOUR) {
		const minutes = Math.floor(seconds / SECONDS_PER_MINUTE);
		const remainingSeconds = seconds % SECONDS_PER_MINUTE;
		if (remainingSeconds === 0) {
			return `${minutes} ${pluralize(minutes, 'минута', 'минуты', 'минут')}`;
		}
		return `${minutes} мин ${remainingSeconds} с`;
	}

	const hours = Math.floor(seconds / SECONDS_PER_HOUR);
	const remainingMinutes = Math.floor((seconds % SECONDS_PER_HOUR) / SECONDS_PER_MINUTE);
	if (remainingMinutes === 0) {
		return `${hours} ${pluralize(hours, 'час', 'часа', 'часов')}`;
	}
	return `${hours} ч ${remainingMinutes} мин`;
}

const MOSCOW_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: '2-digit',
	month: '2-digit',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit',
	timeZone: 'Europe/Moscow'
});

function formatMoscowDateTime(value: string | number | Date): string {
	return MOSCOW_DATE_TIME_FORMATTER.format(new Date(value));
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

	return formatMoscowDateTime(date);
}

const MOSCOW_TIME_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	hour: '2-digit',
	minute: '2-digit',
	timeZone: 'Europe/Moscow'
});

/** Wall-clock HH:MM in the festival timezone, e.g. an event's expected start. */
export function formatMoscowTime(value: string | number | Date): string {
	return MOSCOW_TIME_FORMATTER.format(new Date(value));
}

const MOSCOW_DAY_MONTH_FORMATTER = new Intl.DateTimeFormat('ru-RU', {
	day: '2-digit',
	month: '2-digit',
	timeZone: 'Europe/Moscow'
});

// Y-M-D in Moscow time, used only to compare calendar days regardless of the
// device's own timezone (en-CA gives a stable "2026-06-19" shape).
const MOSCOW_DAY_KEY_FORMATTER = new Intl.DateTimeFormat('en-CA', {
	year: 'numeric',
	month: '2-digit',
	day: '2-digit',
	timeZone: 'Europe/Moscow'
});

/**
 * Format when cached data was last synced, for the offline stale notice. Caching
 * may have happened days earlier (installed at home, opened at the venue), so the
 * day is always shown unless it is today/yesterday. Moscow time, like the rest of
 * the app.
 */
export function formatSyncedAt(timestamp: number): string {
	const target = new Date(timestamp);
	const time = MOSCOW_TIME_FORMATTER.format(target);

	const now = new Date();
	const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
	const targetDay = MOSCOW_DAY_KEY_FORMATTER.format(target);

	if (targetDay === MOSCOW_DAY_KEY_FORMATTER.format(now)) {
		return `сегодня в ${time}`;
	}
	if (targetDay === MOSCOW_DAY_KEY_FORMATTER.format(yesterday)) {
		return `вчера в ${time}`;
	}
	return `${MOSCOW_DAY_MONTH_FORMATTER.format(target)} в ${time}`;
}

/**
 * Countdown label for an upcoming event: how many acts away (drift-proof) plus
 * the absolute expected start time as an anchor when known. On a schedule that
 * drifts, the queue distance is always exact, while the "≈ HH:MM" survives being
 * read minutes later — see ADR-0008.
 *
 * An expected time already in the past means the data is a stale snapshot (the
 * show drifted since the last poll), so showing it would be visibly wrong —
 * fall back to the queue distance alone.
 */
export function formatUntil(queueUntil: number, expectedStartTime: string | null): string {
	const base = `Через ${queueUntil} ${pluralize(queueUntil, 'выступление', 'выступления', 'выступлений')}`;
	if (!expectedStartTime || new Date(expectedStartTime).getTime() <= Date.now()) {
		return base;
	}
	return `${base} · ≈ ${formatMoscowTime(expectedStartTime)}`;
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
