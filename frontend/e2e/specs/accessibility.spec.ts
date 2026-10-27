import type { Page } from '@playwright/test';

import type {
	GetVotingNominationOutput,
	GetVotingStatusOutput,
	ListVotingNominationsOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';

async function settleHomeCountdown(page: Page): Promise<void> {
	await page.waitForFunction(() => {
		const cells = Array.from(document.querySelectorAll('.countdown-cell'));
		return cells.every((cell) => getComputedStyle(cell).opacity === '1');
	});
}

const COLOR_SCHEMES = ['light', 'dark'] as const;

const HERO = 'section[aria-labelledby="hero-heading"]';

test.describe('accessibility (axe)', { tag: '@a11y' }, () => {
	test.use({ contextOptions: { reducedMotion: 'reduce' } });

	for (const colorScheme of COLOR_SCHEMES) {
		test.describe(`${colorScheme} theme`, () => {
			test.use({ colorScheme });

			test('home has no WCAG A/AA violations for a guest', async ({ page, expectAccessible }) => {
				await page.goto('/');
				await expect(page.getByRole('heading', { level: 1, name: 'Главная' })).toBeVisible();
				await settleHomeCountdown(page);

				await expectAccessible({ contrastCheckedByHand: [HERO] });
			});

			test('home has no WCAG A/AA violations for a logged-in visitor', async ({
				page,
				api,
				expectAccessible
			}) => {
				api.use(loggedInAs());
				await page.goto('/');
				await expect(page.locator('#app-splash')).toHaveCount(0);
				await settleHomeCountdown(page);

				await expectAccessible({ contrastCheckedByHand: [HERO] });
			});

			test('the open voting list has no WCAG A/AA violations', async ({
				page,
				api,
				expectAccessible
			}) => {
				api.use({
					'GET /voting/status': json<GetVotingStatusOutput>({
						can_vote: true,
						status: 'open',
						voting_starts_at: null,
						voting_ends_at: null
					}),
					'GET /voting/nominations': json<ListVotingNominationsOutput>({
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

				await expectAccessible();
			});

			test('an open nomination ballot has no WCAG A/AA violations', async ({
				page,
				api,
				expectAccessible
			}) => {
				api.use(loggedInAs());
				api.use({
					'GET /voting/status': json<GetVotingStatusOutput>({
						can_vote: true,
						status: 'open',
						voting_starts_at: null,
						voting_ends_at: null
					}),
					'GET /voting/nominations/best-cosplay': json<GetVotingNominationOutput>({
						id: '01890000-0000-7000-8000-0000000000b1',
						code: 'best-cosplay',
						title: 'Лучший косплей',
						works_url: null,
						participants_count: 2,
						user_vote: null,
						participants: [
							{
								id: '01890000-0000-7000-8000-0000000000c1',
								title: 'Косплей на Аи-тян',
								voting_number: 1,
								votes_count: 3,
								user_vote: null
							},
							{
								id: '01890000-0000-7000-8000-0000000000c2',
								title: 'Косплей на Мику',
								voting_number: null,
								votes_count: 0,
								user_vote: null
							}
						]
					})
				});
				await page.goto('/voting/best-cosplay');
				await expect(
					page.getByRole('button', { name: 'Голосовать за Косплей на Аи-тян' })
				).toBeVisible();

				await expectAccessible();
			});

			test('the profile hub has no WCAG A/AA violations for a guest', async ({
				page,
				expectAccessible
			}) => {
				await page.goto('/profile');
				await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();

				await expectAccessible();
			});

			test('the profile hub has no WCAG A/AA violations for an organizer', async ({
				page,
				api,
				expectAccessible
			}) => {
				api.use(organizer());
				await page.goto('/profile');
				await expect(page.getByRole('link', { name: 'Инструменты' })).toBeVisible();

				await expectAccessible();
			});
		});
	}
});
