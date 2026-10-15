import { expect, test } from '../fixtures';

// The UI follows the browser's language until the visitor picks one in the
// profile; the pick is saved on the device and wins from then on.
test.describe('interface language', () => {
	test.describe('English browser', () => {
		test.use({ locale: 'en-US' });

		test('shows English and a lang attribute to match', async ({ page, api }) => {
			await page.goto('/profile');

			await expect(page.getByRole('main').getByRole('link', { name: 'Log in' })).toBeVisible();
			await expect(page.locator('html')).toHaveAttribute('lang', 'en');
			expect(api.unmatched).toEqual([]);
		});

		test('switches to Russian from the profile and remembers it', async ({ page }) => {
			await page.goto('/profile');

			await page.getByRole('button', { name: 'Русский' }).click();
			await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();
			await expect(page.locator('html')).toHaveAttribute('lang', 'ru');

			await page.reload();
			await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();
		});
	});

	test.describe('German browser', () => {
		test.use({ locale: 'de-DE' });

		test('falls back to English', async ({ page }) => {
			await page.goto('/profile');

			await expect(page.getByRole('main').getByRole('link', { name: 'Log in' })).toBeVisible();
		});
	});

	test.describe('Russian browser', () => {
		test.use({ locale: 'ru-RU' });

		test('shows Russian and switches to English', async ({ page }) => {
			await page.goto('/profile');
			await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();

			await page.getByRole('button', { name: 'English' }).click();
			await expect(page.getByRole('main').getByRole('link', { name: 'Log in' })).toBeVisible();
		});
	});
});
