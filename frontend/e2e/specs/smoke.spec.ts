import { expect, loggedInAs, test } from '../fixtures';

test.describe('app boot', { tag: ['@smoke', '@critical'] }, () => {
	test('renders the home shell for a logged-out visitor', async ({ page, api }) => {
		await page.goto('/');

		// The boot splash is removed once the root layout mounts — proof the SPA
		// booted rather than erroring on its first data loads.
		await expect(page.locator('#app-splash')).toHaveCount(0);
		await expect(page).toHaveTitle('ФАН ФАН');
		await expect(page.getByRole('heading', { name: 'ФАН ФАН 2026' })).toBeVisible();

		// Guest affordance: the login entry point is offered.
		await expect(page.getByRole('link', { name: 'Войти' }).first()).toBeVisible();

		// The baseline covered every boot request — nothing hit the loud 404.
		expect(api.unmatched).toEqual([]);
	});

	test('shows the account surface for a logged-in visitor', async ({ page, api }) => {
		api.use(loggedInAs());
		await page.goto('/');

		await expect(page.locator('#app-splash')).toHaveCount(0);
		// A logged-in user is not offered the login link on the home surface.
		await expect(page.getByRole('link', { name: 'Войти' })).toHaveCount(0);
		expect(api.unmatched).toEqual([]);
	});
});
