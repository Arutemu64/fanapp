import { emitSse, expect, test } from '../fixtures';

test.describe('realtime (SSE)', () => {
	test('a schedule_updated event refetches the schedule', async ({ page, api }) => {
		await page.goto('/schedule');
		// Wait until the page has done its initial schedule load and attached its SSE
		// listener before emitting.
		await expect.poll(() => api.countCalls('GET /schedule/')).toBeGreaterThanOrEqual(1);

		const before = api.countCalls('GET /schedule/');
		await emitSse(page, 'schedule_updated', {});

		// The page invalidates 'app:schedule' on the event, which re-runs its load.
		await expect.poll(() => api.countCalls('GET /schedule/')).toBeGreaterThan(before);
		expect(api.unmatched).toEqual([]);
	});
});
