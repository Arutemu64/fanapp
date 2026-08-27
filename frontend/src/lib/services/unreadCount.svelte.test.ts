import { beforeEach, describe, expect, it, vi } from 'vitest';

// The service reads /notifications/unread-count through createApiClient(); a
// hoisted fake lets each test control the count that refresh() sees.
const server = vi.hoisted((): { count: number; ok: boolean; error: unknown } => ({
	count: 0,
	ok: true,
	error: undefined
}));

vi.mock('$lib/api', () => ({
	createApiClient: () => ({
		GET: () =>
			Promise.resolve({
				data: { count: server.count },
				error: server.error,
				response: { ok: server.ok }
			})
	})
}));

import { UnreadCountService } from './unreadCount.svelte';

beforeEach(() => {
	server.count = 0;
	server.ok = true;
	server.error = undefined;
});

describe('UnreadCountService seed', () => {
	it('applies while the count is still provisional', () => {
		const service = new UnreadCountService();
		service.seed(5);
		expect(service.count).toBe(5);
	});

	it('does not overwrite an authoritative zero from refresh with a stale seed', async () => {
		const service = new UnreadCountService();
		// The server has cleared everything before the slow streamed seed resolves.
		server.count = 0;
		await service.refresh();
		expect(service.count).toBe(0);

		// The seed carries an older, positive snapshot — it must not resurrect it.
		service.seed(5);
		expect(service.count).toBe(0);
	});

	it('does not overwrite a cleared count with a later seed', () => {
		const service = new UnreadCountService();
		service.clear();
		service.seed(5);
		expect(service.count).toBe(0);
	});

	it('is overridden by a later authoritative refresh', async () => {
		const service = new UnreadCountService();
		service.seed(3);
		expect(service.count).toBe(3);

		server.count = 7;
		await service.refresh();
		expect(service.count).toBe(7);
	});
});
