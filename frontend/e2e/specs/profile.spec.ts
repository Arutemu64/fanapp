import { readFileSync } from 'node:fs';

import type { OAuthProvidersOutput } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, problem, test } from '../fixtures';

const BLANK_PNG =
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC';

test.describe('profile hub', () => {
	test('offers a guest the login entry point, returning to the hub', async ({ page }) => {
		await page.goto('/profile');

		const login = page.getByRole('main').getByRole('link', { name: 'Войти' });
		await expect(login).toBeVisible();
		await expect(login).toHaveAttribute('href', '/login?next=%2Fprofile');
		await expect(page.getByRole('button', { name: 'Выйти' })).toHaveCount(0);
	});

	test('carries the return path through a social login start', async ({ page, api }) => {
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
		await expect(main.getByRole('link', { name: /@ЛунныйЛис07/ })).toBeVisible();
		await expect(main.getByRole('link', { name: /Билет/ })).toContainText('Не привязан');
		await expect(main.getByRole('link', { name: /Уведомления/ })).toContainText('Выключены');
		await expect(main.getByRole('link', { name: 'Обратная связь' })).toBeVisible();
		await expect(main.getByRole('link', { name: 'Инструменты' })).toHaveCount(0);
		await expect(main.getByRole('button', { name: 'Выйти' })).toBeVisible();
	});

	test('counts linked VK as a notification channel on the hub', async ({ page, api }) => {
		api.use(loggedInAs({ social_identities: [{ provider: 'vk', messages_allowed: true }] }));
		await page.goto('/profile');

		await expect(page.getByRole('main').getByRole('link', { name: /Уведомления/ })).toContainText(
			'Включены'
		);
	});

	test('tells a VK user the community cannot write to them yet', async ({ page, api }) => {
		api.use({
			...loggedInAs({ social_identities: [{ provider: 'vk', messages_allowed: false }] }),
			'POST /me/connections/vk/messages-check': json({ messages_allowed: false })
		});
		await page.goto('/profile/notifications');

		await expect(page.getByText('Сообщество пока не может тебе писать')).toBeVisible();
		expect(api.countCalls('POST /me/connections/vk/messages-check')).toBeGreaterThan(0);
	});

	test('links an organizer to the toolbox and keeps the tab lit there', async ({ page, api }) => {
		api.use(organizer());
		await page.goto('/profile');

		await page.getByRole('main').getByRole('link', { name: 'Инструменты' }).click();
		await expect(page).toHaveURL('/tools');

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
				return problem('TICKET_NOT_FOUND', 404);
			}
		});
		await page.goto('/profile/ticket');

		const field = page.getByLabel('Номер билета');
		await field.fill('fan-7k4q9m');
		await field.press('Enter');

		await expect(field).toHaveAttribute('aria-invalid', 'true');
		await expect(page.getByRole('alert')).toHaveText('Билет не найден');
		expect(sentBarcode).toBe('fan-7k4q9m');
	});

	test('links a ticket from a screenshot picked in the scanner', async ({ page, api }) => {
		let sentBarcode: unknown;
		api.use({
			...loggedInAs(),
			'POST /me/ticket': (route) => {
				sentBarcode = (route.request().postDataJSON() as { barcode: string }).barcode;
				return problem('TICKET_NOT_FOUND', 404);
			}
		});
		await page.goto('/profile/ticket');

		await page.getByRole('button', { name: 'Сканировать билет' }).click();
		const dialog = page.getByRole('dialog', { name: 'Сканирование билета' });
		await dialog.locator('input[type="file"]').setInputFiles({
			name: 'ticket.jpg',
			mimeType: 'image/jpeg',
			buffer: readFileSync(new URL('../media/ticket-qr.mjpeg', import.meta.url))
		});

		await expect(dialog).toHaveCount(0);
		await expect(page.getByLabel('Номер билета')).toHaveValue('1234567890123456');
		expect(sentBarcode).toBe('1234567890123456');
	});

	test('drops a screenshot read that finishes after the scanner was cancelled', async ({
		page,
		api
	}) => {
		let linkAttempts = 0;
		api.use({
			...loggedInAs(),
			'POST /me/ticket': () => {
				linkAttempts += 1;
				return problem('TICKET_NOT_FOUND', 404);
			}
		});
		let releaseDecoder = () => {};
		await page.route('**/*.wasm', (route) => {
			releaseDecoder = () => void route.continue();
		});
		await page.goto('/profile/ticket');

		const scan = page.getByRole('button', { name: 'Сканировать билет' });
		const dialog = page.getByRole('dialog', { name: 'Сканирование билета' });
		await scan.click();
		await dialog.locator('input[type="file"]').setInputFiles({
			name: 'ticket.jpg',
			mimeType: 'image/jpeg',
			buffer: readFileSync(new URL('../media/ticket-qr.mjpeg', import.meta.url))
		});
		await dialog.getByRole('button', { name: 'Отмена' }).click();
		await expect(dialog).toHaveCount(0);

		await scan.click();
		await expect(dialog).toBeVisible();
		releaseDecoder();
		await dialog.locator('input[type="file"]').setInputFiles({
			name: 'blank.png',
			mimeType: 'image/png',
			buffer: Buffer.from(BLANK_PNG, 'base64')
		});

		await expect(dialog.getByText('На изображении не нашлось кода')).toBeVisible();
		await expect(dialog).toBeVisible();
		expect(linkAttempts).toBe(0);
	});
});

test.describe('logging out', { tag: '@critical' }, () => {
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
		expect(report).toContain('Аккаунт: @ЛунныйЛис07');
		expect(report).toContain('Сборка целиком: 0123456789abcdef0123456789abcdef01234567');
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
			'PATCH /me': (route) => {
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
	});
});

test.describe('account dialogs start fresh on reopen', () => {
	test('edit profile drops an unsaved username', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile/account');
		const dialog = page.getByRole('dialog', { name: 'Редактирование профиля' });
		const username = dialog.getByLabel('Имя пользователя');

		await page.getByRole('button', { name: 'Редактировать' }).click();
		await username.fill('ЯсныйСокол05');
		await page.keyboard.press('Escape');
		await expect(dialog).toBeHidden();

		await page.getByRole('button', { name: 'Редактировать' }).click();
		await expect(username).toHaveValue('ЛунныйЛис07');
	});

	test('change password drops the typed password and its error', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/profile/account');
		const dialog = page.getByRole('dialog', { name: 'Изменение пароля' });
		const newPassword = dialog.getByLabel('Новый пароль', { exact: true });

		await page.getByRole('button', { name: 'Изменить' }).click();
		await newPassword.fill('short');
		await newPassword.press('Enter');
		await expect(dialog.getByText(/^Новый пароль должен быть/)).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(dialog).toBeHidden();

		await page.getByRole('button', { name: 'Изменить' }).click();
		await expect(newPassword).toHaveValue('');
		await expect(dialog.getByText(/^Новый пароль должен быть/)).toBeHidden();
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
	});
});
