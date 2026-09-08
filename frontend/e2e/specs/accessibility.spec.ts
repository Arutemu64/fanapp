import type { ApiSchemas } from '../fixtures';

import { expect, json, loggedInAs, test } from '../fixtures';

// axe scans the *rendered* page, so each scan waits for a stable landmark first —
// analysing mid-boot would flag the splash, not the app. `color-contrast` is parked
// as known token debt in support/axe.ts; every other WCAG A/AA rule is enforced.
test.describe('accessibility (axe)', { tag: '@a11y' }, () => {
	test('home has no WCAG A/AA violations for a guest', async ({ page, makeAxeBuilder }) => {
		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'ФАН ФАН 2026' })).toBeVisible();

		const { violations } = await makeAxeBuilder().analyze();
		expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
	});

	test('home has no WCAG A/AA violations for a logged-in visitor', async ({
		page,
		api,
		makeAxeBuilder
	}) => {
		api.use(loggedInAs());
		await page.goto('/');
		await expect(page.locator('#app-splash')).toHaveCount(0);

		const { violations } = await makeAxeBuilder().analyze();
		expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
	});

	test('the open voting list has no WCAG A/AA violations', async ({
		page,
		api,
		makeAxeBuilder
	}) => {
		api.use({
			'GET /voting/status': json<ApiSchemas['GetVotingStateOutput']>({
				can_vote: true,
				status: 'open',
				voting_start: null,
				voting_end: null
			}),
			'GET /voting/nominations': json<ApiSchemas['ListVotingNominationsOutput']>({
				nominations: [
					{
						id: '01890000-0000-7000-8000-0000000000aa',
						code: 'best-cosplay',
						title: 'Лучший косплей',
						works_url: null,
						participants_count: 3,
						user_vote: null
					}
				]
			})
		});
		await page.goto('/voting');
		await expect(page.getByText('Лучший косплей')).toBeVisible();

		const { violations } = await makeAxeBuilder().analyze();
		expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
	});
});
