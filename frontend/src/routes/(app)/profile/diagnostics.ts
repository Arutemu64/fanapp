import { formatRelativeTime } from '#lib/utils/formatters.js';

/**
 * What the diagnostics sheet knows about this device, gathered once when it
 * opens. Plain data so the rows and the copied report can be tested without a
 * browser; the sheet collects it.
 */
export interface DiagnosticsSnapshot {
	version: string;
	/** Full commit SHA of the bundle; empty on a build outside CI. */
	build: string;
	/** `@username · role`, or null for a guest. */
	account: string | null;
	installed: boolean;
	userAgent: string;
	serverReachable: boolean;
	deviceOnline: boolean;
	serviceWorker: ServiceWorkerStatus;
	push: PushDiagnostics;
	storage: StorageDiagnostics;
	cache: CacheEntry[];
}

export type ServiceWorkerStatus =
	'unsupported' | 'none' | 'installing' | 'active' | 'update-waiting';

export interface PushDiagnostics {
	permission: NotificationPermission | 'unsupported';
	subscribed: boolean;
	/** Host of the push service endpoint (FCM, Mozilla, Apple), which tells browsers apart. */
	pushService: string | null;
	/** Whether the server knows this endpoint; null when it was not or could not be asked. */
	serverRegistered: boolean | null;
}

export interface StorageDiagnostics {
	usageBytes: number | null;
	quotaBytes: number | null;
	/** Exempt from eviction under storage pressure; null where the API is missing. */
	persisted: boolean | null;
}

export interface CacheEntry {
	label: string;
	updatedAt: number;
}

export interface DiagnosticsRow {
	label: string;
	value: string;
}

export interface DiagnosticsSection {
	title: string;
	rows: DiagnosticsRow[];
}

/**
 * The saved offline screens by query operation id, in the order the sheet lists
 * them. Only what is persisted for offline use (the root layout's
 * OFFLINE_QUERY_KEYS) is worth showing: its age is what a stale screen shows.
 */
export const CACHE_LABELS: Record<string, string> = {
	getCurrentUser: 'Профиль',
	getPublicConfig: 'Настройки фестиваля',
	getSchedule: 'Программа',
	getSubscriptions: 'Подписки',
	listUserNotifications: 'Уведомления'
};

const SERVICE_WORKER_LABELS: Record<ServiceWorkerStatus, string> = {
	unsupported: 'Не поддерживается',
	none: 'Не установлен',
	installing: 'Устанавливается',
	active: 'Работает',
	'update-waiting': 'Ждёт перезапуска с обновлением'
};

const PERMISSION_LABELS: Record<PushDiagnostics['permission'], string> = {
	granted: 'Разрешено',
	denied: 'Запрещено',
	default: 'Не спрашивали',
	unsupported: 'Не поддерживается'
};

function yesNo(value: boolean): string {
	return value ? 'Да' : 'Нет';
}

function formatBytes(bytes: number): string {
	const megabytes = bytes / (1024 * 1024);
	if (megabytes < 1024) {
		return `${megabytes.toLocaleString('ru-RU', { maximumFractionDigits: 1 })}\u00A0МБ`;
	}
	const gigabytes = megabytes / 1024;
	return `${gigabytes.toLocaleString('ru-RU', { maximumFractionDigits: 1 })}\u00A0ГБ`;
}

function storageUsage(storage: StorageDiagnostics): string {
	if (storage.usageBytes === null) return 'Неизвестно';
	if (storage.quotaBytes === null) return formatBytes(storage.usageBytes);
	return `${formatBytes(storage.usageBytes)} из ${formatBytes(storage.quotaBytes)}`;
}

function serverRegistration(push: PushDiagnostics): string {
	if (push.serverRegistered === null) return 'Не проверено';
	return push.serverRegistered ? 'Знает это устройство' : 'Не знает это устройство';
}

function connection(snapshot: DiagnosticsSnapshot): string {
	if (snapshot.serverReachable) return 'Сервер доступен';
	if (!snapshot.deviceOnline) return 'Нет интернета';
	// The device has a network but the probe can't reach us: a captive portal, a
	// dead VPN or an outage — worth telling apart in a report.
	return 'Интернет есть, сервер недоступен';
}

export function buildSections(snapshot: DiagnosticsSnapshot, now: number): DiagnosticsSection[] {
	const build: DiagnosticsRow[] = [
		{ label: 'Версия', value: snapshot.version || 'Без номера' },
		{ label: 'Сборка', value: snapshot.build.slice(0, 7) || 'Неизвестно' },
		{ label: 'Офлайн-режим', value: SERVICE_WORKER_LABELS[snapshot.serviceWorker] },
		{ label: 'На главном экране', value: yesNo(snapshot.installed) }
	];

	const push: DiagnosticsRow[] = [
		{ label: 'Разрешение', value: PERMISSION_LABELS[snapshot.push.permission] },
		{ label: 'Подписка в браузере', value: yesNo(snapshot.push.subscribed) }
	];
	if (snapshot.push.pushService) {
		push.push({ label: 'Сервис доставки', value: snapshot.push.pushService });
	}
	push.push({ label: 'Сервер', value: serverRegistration(snapshot.push) });

	const cache: DiagnosticsRow[] = snapshot.cache.map((entry) => ({
		label: entry.label,
		value: formatRelativeTime(entry.updatedAt, now)
	}));
	if (cache.length === 0) {
		cache.push({ label: 'Сохранённые экраны', value: 'Нет' });
	}
	cache.push({ label: 'Занято', value: storageUsage(snapshot.storage) });
	if (snapshot.storage.persisted !== null) {
		cache.push({ label: 'Защищено от очистки', value: yesNo(snapshot.storage.persisted) });
	}

	return [
		{ title: 'Приложение', rows: build },
		{ title: 'Связь', rows: [{ label: 'Сейчас', value: connection(snapshot) }] },
		{ title: 'Пуш-уведомления', rows: push },
		{ title: 'Сохранённые данные', rows: cache }
	];
}

/**
 * The plain-text block "Скопировать отчёт" puts on the clipboard, for sending
 * to the organisers over whatever channel is at hand. Carries what the sheet shows plus
 * what a person can't read out loud: the full SHA and the user agent.
 */
export function formatReport(snapshot: DiagnosticsSnapshot, now: number): string {
	const lines = [
		'ФАН ФАН — диагностика',
		`Время: ${new Date(now).toISOString()}`,
		`Аккаунт: ${snapshot.account ?? 'гость'}`
	];
	for (const section of buildSections(snapshot, now)) {
		lines.push('', section.title);
		for (const row of section.rows) {
			lines.push(`${row.label}: ${row.value}`);
		}
	}
	lines.push(
		'',
		`Сборка целиком: ${snapshot.build || 'неизвестно'}`,
		`Браузер: ${snapshot.userAgent}`
	);
	return lines.join('\n');
}
