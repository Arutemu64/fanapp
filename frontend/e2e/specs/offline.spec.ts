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

	test('the connection banner re-checks on tap and confirms the recovery', async ({
		page,
		api
	}) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { level: 1, name: 'Главная' })).toBeVisible();

		// The app trusts an `offline` event at once. Dispatched by hand rather than via
		// context.setOffline, which would also fail the build's own chunk loads (and a
		// mocked route still fulfils under it); the aborted health check keeps the
		// app's probes from recovering under the test.
		api.use({ 'GET /debug/health': (route) => route.abort() });
		await page.evaluate(() => window.dispatchEvent(new Event('offline')));
		await expect(page.getByRole('status').getByText('Нет связи с сервером')).toBeAttached();

		// The strip holds for at least 4s, so the button is still there even if the
		// background poll happens to win the race to the healthy endpoint.
		api.use({ 'GET /debug/health': json({ status: 'healthy' }) });
		await page.getByRole('button', { name: 'Повторить' }).click();

		// Shown once the offline wording has had its minimum time on screen.
		await expect(page.getByRole('status').getByText('Связь восстановлена')).toBeAttached({
			timeout: 10_000
		});
		await expect(page.getByRole('button', { name: 'Повторить' })).toHaveCount(0);
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
