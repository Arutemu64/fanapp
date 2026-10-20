import { expect, test } from '../fixtures';

test.describe('guide articles', () => {
	test('a row on Home opens its article', async ({ page }) => {
		await page.goto('/');

		await page.getByRole('link', { name: /Ярмарка/ }).click();

		await expect(page).toHaveURL('/guide/fair');
		await expect(page.getByText('Почти 500', { exact: false })).toBeVisible();
	});

	test('the back arrow leads Home even when the article is opened directly', async ({ page }) => {
		await page.goto('/guide/fair');

		await page.getByRole('link', { name: 'На главную', exact: true }).click();

		await expect(page).toHaveURL('/');
	});

	test('an unknown article shows the error page', async ({ page }) => {
		await page.goto('/guide/no-such-article');

		await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible();
	});
});
