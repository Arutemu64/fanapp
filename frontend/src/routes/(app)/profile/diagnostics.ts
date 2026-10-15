import { intlLocale } from '#lib/i18n/locale.js';
import { m } from '#lib/paraglide/messages.js';
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
export const CACHE_LABELS: Record<string, () => string> = {
	getCurrentUser: m.nav_profile,
	getPublicConfig: m.tool_settings,
	getSchedule: m.nav_schedule,
	getSubscriptions: m.diag_subscriptions,
	listUserNotifications: m.notifications_title
};

const SERVICE_WORKER_LABELS: Record<ServiceWorkerStatus, () => string> = {
	unsupported: m.diag_unsupported,
	none: m.status_not_set,
	installing: m.diag_sw_installing,
	active: m.diag_sw_active,
	'update-waiting': m.diag_sw_update_waiting
};

const PERMISSION_LABELS: Record<PushDiagnostics['permission'], () => string> = {
	granted: m.diag_permission_granted,
	denied: m.diag_permission_denied,
	default: m.diag_permission_default,
	unsupported: m.diag_unsupported
};

function yesNo(value: boolean): string {
	return value ? m.common_yes() : m.common_no();
}

function formatBytes(bytes: number): string {
	const megabytes = bytes / (1024 * 1024);
	if (megabytes < 1024) {
		return m.diag_size_mb({
			size: megabytes.toLocaleString(intlLocale(), { maximumFractionDigits: 1 })
		});
	}
	const gigabytes = megabytes / 1024;
	return m.diag_size_gb({
		size: gigabytes.toLocaleString(intlLocale(), { maximumFractionDigits: 1 })
	});
}

function storageUsage(storage: StorageDiagnostics): string {
	if (storage.usageBytes === null) return m.common_unknown();
	if (storage.quotaBytes === null) return formatBytes(storage.usageBytes);
	return m.diag_storage_usage({
		used: formatBytes(storage.usageBytes),
		total: formatBytes(storage.quotaBytes)
	});
}

function serverRegistration(push: PushDiagnostics): string {
	if (push.serverRegistered === null) return m.diag_not_checked();
	return push.serverRegistered ? m.diag_server_knows_device() : m.diag_server_unknown_device();
}

function connection(snapshot: DiagnosticsSnapshot): string {
	if (snapshot.serverReachable) return m.diag_server_reachable();
	if (!snapshot.deviceOnline) return m.connection_no_internet();
	// The device has a network but the probe can't reach us: a captive portal, a
	// dead VPN or an outage — worth telling apart in a report.
	return m.diag_server_unreachable();
}

export function buildSections(snapshot: DiagnosticsSnapshot, now: number): DiagnosticsSection[] {
	const build: DiagnosticsRow[] = [
		{ label: m.diag_version(), value: snapshot.version || m.diag_no_version() },
		{ label: m.diag_build(), value: snapshot.build.slice(0, 7) || m.common_unknown() },
		{ label: m.diag_offline_mode(), value: SERVICE_WORKER_LABELS[snapshot.serviceWorker]() },
		{ label: m.diag_home_screen(), value: yesNo(snapshot.installed) }
	];

	const push: DiagnosticsRow[] = [
		{ label: m.diag_permission(), value: PERMISSION_LABELS[snapshot.push.permission]() },
		{ label: m.diag_browser_subscription(), value: yesNo(snapshot.push.subscribed) }
	];
	if (snapshot.push.pushService) {
		push.push({ label: m.diag_delivery_service(), value: snapshot.push.pushService });
	}
	push.push({ label: m.diag_server(), value: serverRegistration(snapshot.push) });

	const cache: DiagnosticsRow[] = snapshot.cache.map((entry) => ({
		label: entry.label,
		value: formatRelativeTime(entry.updatedAt, now)
	}));
	if (cache.length === 0) {
		cache.push({ label: m.diag_cached_screens(), value: m.common_no() });
	}
	cache.push({ label: m.diag_storage_used(), value: storageUsage(snapshot.storage) });
	if (snapshot.storage.persisted !== null) {
		cache.push({ label: m.diag_storage_persisted(), value: yesNo(snapshot.storage.persisted) });
	}

	return [
		{ title: m.diag_section_app(), rows: build },
		{
			title: m.diag_section_connection(),
			rows: [{ label: m.common_now(), value: connection(snapshot) }]
		},
		{ title: m.diag_section_push(), rows: push },
		{ title: m.diag_section_cache(), rows: cache }
	];
}

/**
 * The plain-text block "Скопировать отчёт" puts on the clipboard, for sending
 * to the organizers over whatever channel is at hand. Carries what the sheet shows plus
 * what a person can't read out loud: the full SHA and the user agent.
 */
export function formatReport(snapshot: DiagnosticsSnapshot, now: number): string {
	// Widened: message functions return the branded LocalizedString, which would
	// otherwise reject the plain strings pushed below.
	const lines: string[] = [
		m.diag_report_title(),
		m.diag_report_time({ time: new Date(now).toISOString() }),
		m.diag_report_account({ account: snapshot.account ?? m.diag_report_guest() })
	];
	for (const section of buildSections(snapshot, now)) {
		lines.push('', section.title);
		for (const row of section.rows) {
			lines.push(`${row.label}: ${row.value}`);
		}
	}
	lines.push(
		'',
		m.diag_report_full_build({ build: snapshot.build || m.diag_report_unknown() }),
		m.diag_report_browser({ userAgent: snapshot.userAgent })
	);
	return lines.join('\n');
}
