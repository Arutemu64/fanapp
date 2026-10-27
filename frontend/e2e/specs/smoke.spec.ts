import { expect, loggedInAs, test } from '../fixtures';

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

	test('shows the account surface for a logged-in visitor', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/');

		await expect(page.locator('#app-splash')).toHaveCount(0);
		await expect(page.getByRole('link', { name: 'Войти' })).toHaveCount(0);
	});
});
