export function formatDuration(seconds: number): string {
	const m = Math.ceil((seconds % 3600) / 60);
	return `${m} ${pluralize(m, 'минута', 'минуты', 'минут')}`;
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

export function formatUntil(queueUntil: number, timeUntil: number): string {
	const h = Math.floor(timeUntil / 3600);
	const m = Math.ceil((timeUntil % 3600) / 60);
	return `Через ${queueUntil} ${pluralize(queueUntil, 'выступление', 'выступления', 'выступлений')} (${h} ч. ${m.toString().padStart(2, '0')} мин.)`;
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
