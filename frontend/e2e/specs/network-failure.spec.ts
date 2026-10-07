import { expect, test } from '../fixtures';

test.describe('network failure', { tag: '@critical' }, () => {
	test('a dead network yields the retryable error page', async ({ page, api }) => {
		// Simulate the dead network by aborting the reads — `context.setOffline`
		// can't, because a mocked route still fulfils under it.
		api.use({
			'GET /voting/status': (route) => route.abort(),
			'GET /voting/nominations': (route) => route.abort()
		});
		await page.goto('/voting');

		await expect(
			page.getByText('Не удалось связаться с сервером. Попробуй ещё раз.')
		).toBeVisible();
		await expect(page.getByRole('button', { name: 'Попробовать снова' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});
