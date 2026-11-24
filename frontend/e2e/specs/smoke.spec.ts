import { expect, loggedInAs, test } from '../fixtures';

const ENTRY_MODULE = /\/_app\/immutable\/entry\/start\.[^/]+\.js$/;
const UNAVAILABLE_ENTRY = { status: 503, headers: { 'cache-control': 'no-store' } };
const ENTRY_LOAD_ERROR =
	/Failed to load resource.*503|dynamically imported module|Importing a module script failed/i;

test.describe('app boot', { tag: ['@smoke', '@critical'] }, () => {
	test('renders the home shell for a logged-out visitor', async ({ page }) => {
		await page.goto('/');

		await expect(page.locator('#app-splash')).toHaveCount(0);
		await expect(page).toHaveTitle('ФАН ФАН');
		await expect(page.getByRole('heading', { level: 1, name: 'Главная' })).toBeVisible();

		await expect(
			page.getByRole('navigation', { name: 'Разделы' }).getByRole('link', { name: 'Профиль' })
		).toBeVisible();
	});

	test('offers a signed-in visitor a link to attach their ticket', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/');

		await expect(page.locator('#app-splash')).toHaveCount(0);
		const ticket = page.getByRole('link', { name: /Привязать билет/ });
		await expect(ticket).toBeVisible();
		await expect(ticket).toHaveAttribute('href', '/profile/ticket');
	});
});

test.describe('boot recovery', () => {
	test('reloads once when the entry module is temporarily unavailable', async ({
		page,
		consoleErrors
	}) => {
		consoleErrors.allow(ENTRY_LOAD_ERROR);
		let navigations = 0;
		await page.route('**/map', (route) => {
			navigations += 1;
			return route.continue();
		});
		await page.route(ENTRY_MODULE, (route) => {
			const refreshing = route.request().resourceType() === 'fetch';
			return navigations === 1 && !refreshing ? route.fulfill(UNAVAILABLE_ENTRY) : route.continue();
		});

		await page.goto('/map', { waitUntil: 'commit' });

		await expect(page.getByRole('heading', { level: 1, name: 'Карта' })).toBeVisible();
		expect(navigations).toBe(2);
	});

	test('offers a manual reload when the entry module still fails', async ({
		page,
		consoleErrors
	}) => {
		consoleErrors.allow(ENTRY_LOAD_ERROR);
		await page.route(ENTRY_MODULE, (route) => route.fulfill(UNAVAILABLE_ENTRY));
		await page.goto('/map', { waitUntil: 'commit' });

		const retry = page.getByRole('button', { name: 'Обновить страницу' });
		await expect(retry).toBeVisible();
		await expect(retry).toBeFocused();
		await page.unroute(ENTRY_MODULE);
		await retry.press('Enter');

		await expect(page.getByRole('heading', { level: 1, name: 'Карта' })).toBeVisible();
	});
});
