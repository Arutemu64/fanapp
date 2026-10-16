import { emitSse, expect, test } from '../fixtures';

test.describe('realtime (SSE)', { tag: '@critical' }, () => {
	test('a schedule_updated event refetches the schedule', async ({ page, api }) => {
		await page.goto('/schedule');
		// The search field renders once the schedule has arrived, by which time the
		// app shell has mounted and attached its SSE listeners.
		await expect(page.getByRole('textbox', { name: 'Поиск по программе' })).toBeVisible();

		const before = api.countCalls('GET /schedule/');
		await emitSse(page, 'schedule_updated', {});

		// The root layout invalidates the schedule query on the event, which refetches
		// it while the page shows it.
		await expect.poll(() => api.countCalls('GET /schedule/')).toBeGreaterThan(before);
	});
});
