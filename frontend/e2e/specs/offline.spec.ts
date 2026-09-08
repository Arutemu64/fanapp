import { expect, test } from '../fixtures';

test.describe('offline', () => {
	test('voting shows the online-only state when the network is down', async ({ page, api }) => {
		// Voting is uncached and online-only, so a dead network must yield the honest
		// "online only" state, not a generic error. Simulate the dead network by
		// aborting its reads — `context.setOffline` can't, because a mocked route
		// still fulfils under it.
		api.use({
			'GET /voting/status': (route) => route.abort(),
			'GET /voting/nominations': (route) => route.abort()
		});
		await page.goto('/voting');

		await expect(page.getByText('Голосование доступно только онлайн')).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});
