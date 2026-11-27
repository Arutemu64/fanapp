import type { Route } from '@playwright/test';

import { expect, json, loggedInAs, test } from '../fixtures';

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

test.describe('session check recovery', { tag: '@critical' }, () => {
	test('retries the protected destination after a session check fails on a reachable server', async ({
		page,
		api
	}) => {
		api.use({ 'GET /me': json({}, 500) });
		await page.goto('/notifications');

		await expect(page.getByText('Не удалось проверить, выполнен ли вход.')).toBeVisible();
		await expect(page).toHaveURL('/notifications');
		expect(api.countCalls('GET /notifications')).toBe(0);

		api.use(loggedInAs());
		await page.getByRole('button', { name: 'Попробовать снова' }).click();

		await expect(page.getByRole('heading', { name: 'Уведомления' })).toBeVisible();
		await expect(page).toHaveURL('/notifications');
	});

	test('keeps the login return path when the session check times out', async ({ page, api }) => {
		const pendingIdentity = Promise.withResolvers<Route>();
		api.use(loggedInAs());
		await page.route('**/api/me', pendingIdentity.resolve, { times: 1 });

		const loginUrl = '/login?next=%2Fmap%3Ffloor%3D2';
		await page.goto(loginUrl, { waitUntil: 'commit' });
		const identityRequest = await pendingIdentity.promise;
		try {
			await expect(page.getByText('Не удалось проверить, выполнен ли вход.')).toBeVisible({
				timeout: 10_000
			});
			await expect(page).toHaveURL(loginUrl);
			await expect(page.getByRole('button', { name: 'Войти по почте' })).toHaveCount(0);
		} finally {
			await identityRequest.fulfill({ status: 500, json: {} });
		}
		await page.getByRole('button', { name: 'Попробовать снова' }).click();

		await expect(page.getByRole('heading', { level: 1, name: 'Карта' })).toBeVisible();
		await expect(page).toHaveURL('/map?floor=2');
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
