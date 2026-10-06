import type { OAuthProvidersOutput } from '../../src/lib/api/generated';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';

// The Profile tab is the hub for everything without a tab of its own: login for
// guests; account settings, feedback, the org toolbox and logout for members.
test.describe('profile hub', () => {
	test('offers a guest the login entry point, returning to the hub', async ({ page, api }) => {
		await page.goto('/profile');

		const login = page.getByRole('main').getByRole('link', { name: 'Войти' });
		await expect(login).toBeVisible();
		await expect(login).toHaveAttribute('href', '/login?next=%2Fprofile');
		await expect(page.getByRole('button', { name: 'Выйти' })).toHaveCount(0);
		expect(api.unmatched).toEqual([]);
	});

	test('carries the return path through a social login start', async ({ page, api }) => {
		// A social login leaves for the provider, so `next` has to ride along to the
		// backend start route, which keeps it in the OAuth state.
		api.use({
			'GET /auth/oauth/providers': json<OAuthProvidersOutput>({ providers: ['vk'] })
		});
		await page.goto('/login?next=%2Fprofile');

		const vk = page.getByRole('link', { name: 'Войти через VK ID' });
		await expect(vk).toHaveAttribute('href', /\/auth\/oauth\/vk\/start\?next=%2Fprofile$/);
	});

	test('shows a visitor their settings and logout, but no toolbox', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile');

		const main = page.getByRole('main');
		await expect(main.getByRole('link', { name: /@test_visitor/ })).toBeVisible();
		await expect(main.getByRole('link', { name: /Билет/ })).toContainText('Не привязан');
		await expect(main.getByRole('link', { name: 'Обратная связь' })).toBeVisible();
		await expect(main.getByRole('link', { name: 'Инструменты' })).toHaveCount(0);
		await expect(main.getByRole('button', { name: 'Выйти' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('links an organiser to the toolbox and keeps the tab lit there', async ({ page, api }) => {
		api.use(organizer());
		await page.goto('/profile');

		await page.getByRole('main').getByRole('link', { name: 'Инструменты' }).click();
		await expect(page).toHaveURL('/tools');

		// The toolbox has no tab of its own, so the Profile tab stays the current one.
		const nav = page.getByRole('navigation', { name: 'Разделы' });
		await expect(nav.getByRole('link', { name: 'Профиль' })).toHaveAttribute(
			'aria-current',
			'page'
		);
	});

	test('opens a settings page behind the hub with a way back', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile');

		await page.getByRole('main').getByRole('link', { name: /Билет/ }).click();
		await expect(page).toHaveURL('/profile/ticket');
		await expect(page.getByRole('heading', { level: 1, name: 'Билет' })).toBeVisible();

		await page.getByRole('link', { name: 'Назад в профиль' }).click();
		await expect(page).toHaveURL('/profile');
	});
});
