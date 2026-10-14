import { describe, expect, it } from 'vitest';

import { buildSections, type DiagnosticsSnapshot, formatReport } from './diagnostics';

const NOW = Date.UTC(2026, 9, 14, 12, 0, 0);

function snapshot(overrides: Partial<DiagnosticsSnapshot> = {}): DiagnosticsSnapshot {
	return {
		version: '1.4.0',
		build: '0123456789abcdef',
		account: '@test_visitor · Гость',
		installed: false,
		userAgent: 'TestBrowser/1.0',
		serverReachable: true,
		deviceOnline: true,
		serviceWorker: 'active',
		push: {
			permission: 'granted',
			subscribed: true,
			pushService: 'fcm.googleapis.com',
			serverRegistered: true
		},
		storage: { usageBytes: 5 * 1024 * 1024, quotaBytes: 100 * 1024 * 1024, persisted: false },
		cache: [{ label: 'Программа', updatedAt: NOW - 5 * 60 * 1000 }],
		...overrides
	};
}

function valueOf(snap: DiagnosticsSnapshot, label: string): string | undefined {
	const rows = buildSections(snap, NOW).flatMap((section) => section.rows);
	return rows.find((row) => row.label === label)?.value;
}

describe('buildSections', () => {
	it('tells a dead server apart from a dead connection', () => {
		expect(valueOf(snapshot({ serverReachable: false }), 'Сейчас')).toBe(
			'Интернет есть, сервер недоступен'
		);
		expect(valueOf(snapshot({ serverReachable: false, deviceOnline: false }), 'Сейчас')).toBe(
			'Нет интернета'
		);
	});

	it('shows how old each saved screen is', () => {
		expect(valueOf(snapshot(), 'Программа')).toBe('5 минут назад');
		expect(valueOf(snapshot({ cache: [] }), 'Сохранённые экраны')).toBe('Нет');
	});

	it('leaves out what the browser does not report', () => {
		const snap = snapshot({
			push: {
				permission: 'unsupported',
				subscribed: false,
				pushService: null,
				serverRegistered: null
			},
			storage: { usageBytes: null, quotaBytes: null, persisted: null }
		});
		expect(valueOf(snap, 'Сервис доставки')).toBeUndefined();
		expect(valueOf(snap, 'Защищено от очистки')).toBeUndefined();
		expect(valueOf(snap, 'Сервер')).toBe('Не проверено');
		expect(valueOf(snap, 'Занято')).toBe('Неизвестно');
	});

	it('shortens the build to the SHA the profile shows', () => {
		expect(valueOf(snapshot(), 'Сборка')).toBe('0123456');
	});

	it('switches to gigabytes for a large quota', () => {
		const storage = { usageBytes: 5 * 1024 * 1024, quotaBytes: 3 * 1024 ** 3, persisted: null };
		expect(valueOf(snapshot({ storage }), 'Занято')).toBe('5\u00A0МБ из 3\u00A0ГБ');
	});
});

describe('formatReport', () => {
	it('carries the full build and user agent for whoever reads it', () => {
		const report = formatReport(snapshot(), NOW);
		expect(report).toContain('Аккаунт: @test_visitor · Гость');
		expect(report).toContain('Сборка целиком: 0123456789abcdef');
		expect(report).toContain('Браузер: TestBrowser/1.0');
		expect(report).toContain('Время: 2026-10-14T12:00:00.000Z');
	});

	it('names a guest', () => {
		expect(formatReport(snapshot({ account: null }), NOW)).toContain('Аккаунт: гость');
	});
});
