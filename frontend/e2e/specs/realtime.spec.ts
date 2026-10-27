import { emitSse, expect, test } from '../fixtures';

test.describe('realtime (SSE)', { tag: '@critical' }, () => {
	test('a schedule_updated event refetches the schedule', async ({ page, api }) => {
		await page.goto('/schedule');
		await expect(page.getByRole('searchbox', { name: 'Поиск по программе' })).toBeVisible();

		const before = api.countCalls('GET /schedule');
		await emitSse(page, 'schedule_updated', {});

		await expect.poll(() => api.countCalls('GET /schedule')).toBeGreaterThan(before);
	});
});
