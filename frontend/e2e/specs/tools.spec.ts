import type { OnlineUsersCountOutput } from '../../src/lib/api/generated/types.gen';

import { expect, json, organizer, test } from '../fixtures';

test.describe('organizer tools', { tag: '@critical' }, () => {
	test('an organizer sees the toolbox', async ({ page, api }) => {
		api.use({
			...organizer(),
			'GET /users/online-count': json<OnlineUsersCountOutput>({ count: 5 })
		});
		await page.goto('/tools');

		await expect(page.getByText('Инструменты для работы на фестивале.')).toBeVisible();
		await expect(page.getByText('сейчас в приложении')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Пользователи' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Синхронизация' })).toBeVisible();
	});

	test('a guest is bounced to login', async ({ page }) => {
		await page.goto('/tools');

		await expect(page).toHaveURL(/\/login\?/);
		await expect(page.getByRole('heading', { level: 1, name: 'Вход' })).toBeVisible();
	});
});
