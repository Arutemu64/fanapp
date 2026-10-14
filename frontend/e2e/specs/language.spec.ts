import { expect, test } from '../fixtures';

// The interface is Russian until someone picks English; the choice lives in
// localStorage (Paraglide's `localStorage` strategy) and applies after a reload.
test.describe('interface language', () => {
	test('stays Russian by default', async ({ page, api }) => {
		await page.goto('/profile');

		await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
		await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('switches to English from the profile and keeps it across reloads', async ({
		page,
		api
	}) => {
		await page.goto('/profile');
		await page
			.getByRole('group', { name: 'Язык интерфейса' })
			.getByRole('button', { name: 'English' })
			.click();

		const main = page.getByRole('main');
		await expect(main.getByRole('link', { name: 'Sign in' })).toBeVisible();
		await expect(page.locator('html')).toHaveAttribute('lang', 'en');
		await expect(
			page
				.getByRole('group', { name: 'Interface language' })
				.getByRole('button', { name: 'English' })
		).toHaveAttribute('aria-pressed', 'true');

		await page.reload();
		await expect(main.getByRole('link', { name: 'Sign in' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});

	test('translates the navigation and returns to Russian', async ({ page, api }) => {
		// Only the first load: the init script re-runs on the reload the switch triggers.
		await page.addInitScript(() => {
			if (!localStorage.getItem('PARAGLIDE_LOCALE')) localStorage.setItem('PARAGLIDE_LOCALE', 'en');
		});
		await page.goto('/profile');

		const nav = page.getByRole('navigation', { name: 'Sections' }).first();
		await expect(nav.getByRole('link', { name: 'Schedule' })).toBeVisible();
		await expect(nav.getByRole('link', { name: 'Voting' })).toBeVisible();

		await page
			.getByRole('group', { name: 'Interface language' })
			.getByRole('button', { name: 'Русский' })
			.click();
		await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();
		expect(api.unmatched).toEqual([]);
	});
});
