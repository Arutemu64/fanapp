import { beforeEach, describe, expect, it, vi } from 'vitest';

// The service reads the unread count through the generated `countUnreadNotifications`
// SDK call; a hoisted fake lets each test control the count that refresh() sees.
const server = vi.hoisted((): { count: number; ok: boolean; error: unknown } => ({
	count: 0,
	ok: true,
	error: undefined
}));

vi.mock('#lib/api/index.js', () => ({
	createApiClient: () => ({})
}));

vi.mock('#lib/api/generated/index.js', () => ({
	countUnreadNotifications: () =>
		Promise.resolve({
			data: { count: server.count },
			error: server.error,
			response: { ok: server.ok }
		})
}));

import { UnreadCountService } from './unreadCount.svelte';

beforeEach(() => {
	server.count = 0;
	server.ok = true;
	server.error = undefined;
});

describe('UnreadCountService', () => {
	it('takes the server total on refresh', async () => {
		const service = new UnreadCountService();
		server.count = 7;
		await service.refresh();
		expect(service.count).toBe(7);
	});

	it('keeps the last known count when a refresh fails', async () => {
		const service = new UnreadCountService();
		server.count = 3;
		await service.refresh();

		server.ok = false;
		server.count = 0;
		await service.refresh();
		expect(service.count).toBe(3);
	});

	it('does not let a refresh that started before a clear restore the old total', async () => {
		const service = new UnreadCountService();
		server.count = 5;
		const inFlight = service.refresh();
		// "Прочитать все" lands while the GET is still in flight.
		service.clear();
		await inFlight;
		expect(service.count).toBe(0);
	});
});
