import { expect, organizer, test } from '../fixtures';

test.describe('organizer tools', { tag: '@critical' }, () => {
	test('an organizer sees the toolbox', async ({ page, api }) => {
		api.use(organizer());
		await page.goto('/tools');

		await expect(
			page.getByText('Для работы организаторов фестиваля.', { exact: false })
		).toBeVisible();
		// A couple of the permission-gated tool cards render for a full-permission org.
		await expect(page.getByRole('link', { name: 'Пользователи' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Синхронизация' })).toBeVisible();

		expect(api.unmatched).toEqual([]);
	});

	test('a guest is bounced to login', async ({ page, api }) => {
		// No persona: the baseline /me/ is a 401 guest, and the protected guard
		// redirects a reachable guest to login, remembering where they were headed.
		await page.goto('/tools');

		await expect(page).toHaveURL(/\/login\?/);
		await expect(page.getByRole('heading', { name: 'Вход в ФАН ФАН' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});
