import { expect, test } from '../fixtures';

test.describe('guide articles', () => {
	test('a hub row opens its article, and the back arrow returns to the guide', async ({ page }) => {
		await page.goto('/guide');

		await page.getByRole('link', { name: /Ярмарка/ }).click();

		await expect(page).toHaveURL('/guide/fair');
		await expect(page.getByText('Почти 500', { exact: false })).toBeVisible();

		await page.goBack();
		await expect(page).toHaveURL('/guide');
	});

	test('an unknown article shows the error page', async ({ page }) => {
		await page.goto('/guide/no-such-article');

		await expect(page.getByRole('heading', { name: /404|не найден/i }).first()).toBeVisible();
	});
});
