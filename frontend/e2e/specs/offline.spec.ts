import { expect, test } from '../fixtures';
import { json } from '../mocks/api';
import { loggedInAs } from '../mocks/personas';

test.describe('offline', { tag: '@critical' }, () => {
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

	test('a cold start with no saved identity shows the offline state, not login', async ({
		page,
		api
	}) => {
		// The identity check runs before the API interceptors exist, so only the root
		// load's own probe tells the protected guard that a failed /me/ means
		// "offline" rather than "guest".
		api.use({
			'GET /me/': (route) => route.abort(),
			'GET /debug/health': (route) => route.abort()
		});
		await page.goto('/notifications');

		// The device still reports a network, so the probe sits out its 5s offline
		// confirm window before giving a verdict.
		await expect(page.getByRole('main').getByText('Нет связи с сервером')).toBeVisible({
			timeout: 10_000
		});
		await expect(page).toHaveURL('/notifications');
	});

	test('a pending offline logout outlives a cache that still holds the user', async ({
		page,
		api
	}) => {
		// The session cookie is still valid until the queued logout reaches the server,
		// so /me/ keeps answering with the user.
		api.use({ ...loggedInAs(), 'POST /auth/logout': json({}) });
		await page.goto('/notifications');
		await expect(page.getByRole('heading', { name: 'Уведомления' })).toBeVisible();

		// The persister saves on a throttle, so wait until the user is on disk.
		await expect
			.poll(() =>
				page.evaluate(
					() =>
						new Promise<string>((resolve) => {
							const open = indexedDB.open('keyval-store');
							open.onsuccess = () => {
								const read = open.result
									.transaction('keyval')
									.objectStore('keyval')
									.get('REACT_QUERY_OFFLINE_CACHE');
								read.onsuccess = () => resolve(JSON.stringify(read.result ?? ''));
							};
						})
				)
			)
			.toContain('getCurrentUser');

		// What an offline logout leaves when the app closes before the next save.
		await page.evaluate(() => localStorage.setItem('fanfan:pending-logout', '1'));
		await page.reload();

		await expect(page).toHaveURL(/\/login\?next=%2Fnotifications$/);
	});
});
