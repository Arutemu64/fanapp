import type { OAuthProvidersOutput } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';

// The Profile tab is the hub for everything without a tab of its own: login for
// guests; account settings, feedback, the organizer toolbox and logout for members.
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
		// No push subscription in a fresh browser: the row says so at a glance.
		await expect(main.getByRole('link', { name: /Уведомления/ })).toContainText('Выключены');
		await expect(main.getByRole('link', { name: 'Обратная связь' })).toBeVisible();
		await expect(main.getByRole('link', { name: 'Инструменты' })).toHaveCount(0);
		await expect(main.getByRole('button', { name: 'Выйти' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('counts linked VK as a notification channel on the hub', async ({ page, api }) => {
		// Push is off in a fresh browser, but VK still delivers, so the row says so.
		api.use(loggedInAs({ social_identities: [{ provider: 'vk' }] }));
		await page.goto('/profile');

		await expect(page.getByRole('main').getByRole('link', { name: /Уведомления/ })).toContainText(
			'Включены'
		);
	});

	test('links an organizer to the toolbox and keeps the tab lit there', async ({ page, api }) => {
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
				sentBarcode = (route.request().postDataJSON() as { barcode: string }).barcode;
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

	test('toggles a setting by tapping its title, without a success toast', async ({ page, api }) => {
		let patched: unknown;
		api.use({
			...loggedInAs(),
			'PATCH /me/settings': (route) => {
				patched = route.request().postDataJSON() as unknown;
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

test.describe('logging out', () => {
	test('asks first, and cancelling keeps the session', async ({ page, api }) => {
		api.use({ ...loggedInAs(), 'POST /auth/logout': json({}) });
		await page.goto('/profile');

		await page.getByRole('main').getByRole('button', { name: 'Выйти' }).click();
		const confirm = page.getByRole('alertdialog', { name: 'Выйти из аккаунта?' });
		await expect(confirm).toBeVisible();

		await confirm.getByRole('button', { name: 'Отмена' }).click();
		await expect(confirm).toBeHidden();
		expect(api.countCalls('POST /auth/logout')).toBe(0);

		await page.getByRole('main').getByRole('button', { name: 'Выйти' }).click();
		await confirm.getByRole('button', { name: 'Выйти' }).click();

		await expect(page).toHaveURL('/');
		expect(api.countCalls('POST /auth/logout')).toBe(1);
	});
});

test.describe('diagnostics', () => {
	test('opens from five taps on the version line and copies a report', async ({ page, api }) => {
		// Captured instead of read back: WebKit rejects `clipboard-write` as an
		// unknown permission, so granting it cannot be shared across projects.
		await page.addInitScript(() => {
			navigator.clipboard.writeText = (text: string) => {
				(window as { copiedText?: string }).copiedText = text;
				return Promise.resolve();
			};
		});
		api.use(loggedInAs());
		await page.goto('/profile');

		const version = page.getByRole('button', { name: /Версия 1\.0\.0/ });
		await version.click({ clickCount: 4 });
		await expect(page.getByRole('dialog', { name: 'Диагностика' })).toHaveCount(0);
		await version.click();

		const dialog = page.getByRole('dialog', { name: 'Диагностика' });
		await expect(dialog).toContainText('Сервер доступен');
		await expect(dialog).toContainText('0123456');

		await dialog.getByRole('button', { name: 'Скопировать отчёт' }).click();
		await expect(page.getByText('Отчёт скопирован')).toBeVisible();
		const report = await page.evaluate(() => (window as { copiedText?: string }).copiedText);
		expect(report).toContain('Аккаунт: @test_visitor');
		expect(report).toContain('Сборка целиком: 0123456789abcdef0123456789abcdef01234567');
		expect(api.unmatched).toEqual([]);
	});
});

test.describe('avatar', () => {
	test('previews a new avatar from the refresh button and saves its seed', async ({
		page,
		api
	}) => {
		let patched: unknown;
		api.use({
			...loggedInAs(),
			'PATCH /me/': (route) => {
				patched = route.request().postDataJSON() as unknown;
				return json({});
			}
		});
		await page.goto('/profile/account');
		await page.getByRole('button', { name: 'Редактировать' }).click();

		const dialog = page.getByRole('dialog', { name: 'Редактирование профиля' });
		const avatar = dialog.locator('img');
		const before = await avatar.getAttribute('src');

		await dialog.getByRole('button', { name: 'Другой аватар' }).click();
		await expect(avatar).not.toHaveAttribute('src', before ?? '');

		await dialog.getByRole('button', { name: 'Сохранить' }).click();
		await expect.poll(() => patched).toEqual({ avatar_seed: expect.stringMatching(/^[\w-]{12}$/) });
		expect(api.unmatched).toEqual([]);
	});
});

// Each account dialog mounts its form inside the dialog content, so closing it
// throws the draft away: reopening must start from the saved state, never from
// a half-typed value or an old error.
test.describe('account dialogs start fresh on reopen', () => {
	test('edit profile drops an unsaved username', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile/account');
		const dialog = page.getByRole('dialog', { name: 'Редактирование профиля' });
		const username = dialog.getByLabel('Имя пользователя');

		await page.getByRole('button', { name: 'Редактировать' }).click();
		await username.fill('draft_name');
		await page.keyboard.press('Escape');
		await expect(dialog).toBeHidden();

		await page.getByRole('button', { name: 'Редактировать' }).click();
		await expect(username).toHaveValue('test_visitor');
		expect(api.unmatched).toEqual([]);
	});

	test('change password drops the typed password and its error', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile/account');
		const dialog = page.getByRole('dialog', { name: 'Изменение пароля' });
		const newPassword = dialog.getByLabel('Новый пароль', { exact: true });

		await page.getByRole('button', { name: 'Изменить' }).click();
		await newPassword.fill('short');
		// Enter, not a tap on the submit button: on a phone the sheet's button sits
		// over the bottom nav, and the pointer left there after the sheet closes
		// would hover-preload the voting tab.
		await newPassword.press('Enter');
		await expect(dialog.getByText(/^Новый пароль должен быть/)).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(dialog).toBeHidden();

		await page.getByRole('button', { name: 'Изменить' }).click();
		await expect(newPassword).toHaveValue('');
		await expect(dialog.getByText(/^Новый пароль должен быть/)).toBeHidden();
		expect(api.unmatched).toEqual([]);
	});

	test('change email returns to the address step', async ({ page, api }) => {
		api.use({ ...loggedInAs(), 'POST /me/email': json({}) });
		await page.goto('/profile/account');
		const dialog = page.getByRole('dialog', { name: 'Добавить почту' });
		const newEmail = dialog.getByLabel('Новая почта');

		await page.getByRole('button', { name: 'Добавить' }).click();
		await newEmail.fill('new@example.com');
		await newEmail.press('Enter');
		await expect(dialog.getByText('Код подтверждения', { exact: true })).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(dialog).toBeHidden();

		await page.getByRole('button', { name: 'Добавить' }).click();
		await expect(newEmail).toBeEditable();
		await expect(newEmail).toHaveValue('');
		expect(api.unmatched).toEqual([]);
	});
});
