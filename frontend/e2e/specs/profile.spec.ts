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

test.describe('profile settings on a phone', () => {
	test('links a ticket from the keyboard and shows a miss under the field', async ({
		page,
		api
	}) => {
		let sentBarcode: unknown;
		api.use({
			...loggedInAs(),
			'POST /me/ticket': (route) => {
				sentBarcode = route.request().postDataJSON().barcode;
				return json({ code: 'TICKET_NOT_FOUND', details: {} }, 404);
			}
		});
		await page.goto('/profile/ticket');

		// The phone keyboard's Enter/«Go» key submits — no reach for the button.
		const field = page.getByLabel('Номер билета');
		await field.fill('fan-7k4q9m');
		await field.press('Enter');

		await expect(field).toHaveAttribute('aria-invalid', 'true');
		await expect(page.getByRole('alert')).toHaveText('Билет не найден');
		expect(sentBarcode).toBe('fan-7k4q9m');
		expect(api.unmatched).toEqual([]);
	});

	test('toggles a setting by tapping its title, without a success toast', async ({
		page,
		api
	}) => {
		let patched: unknown;
		api.use({
			...loggedInAs(),
			'PATCH /me/settings': (route) => {
				patched = route.request().postDataJSON();
				return json({});
			}
		});
		await page.goto('/profile/notifications');

		// The switch is named by its visible title alone (WCAG 2.5.3).
		const allAnnouncements = page.getByRole('switch', { name: 'Все анонсы', exact: true });
		await expect(allAnnouncements).toBeChecked();

		await page.getByText('Все анонсы', { exact: true }).click();

		await expect(allAnnouncements).not.toBeChecked();
		await expect.poll(() => patched).toEqual({ receive_all_announcements: false });
		await expect(page.getByText('Настройки сохранены')).toHaveCount(0);
	});
});
