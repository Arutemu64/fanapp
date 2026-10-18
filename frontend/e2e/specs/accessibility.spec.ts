import type { Page } from '@playwright/test';

import type {
	GetVotingNominationOutput,
	GetVotingStateOutput,
	ListVotingNominationsOutput
} from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';
import { GALLERY_NOW } from '../gallery/data';
import { festivalInProgress } from '../mocks/festival';

// The home hero fades its countdown cells in with a staggered per-cell delay. axe
// reads computed colour, so a cell caught mid-fade blends with its backdrop and
// reports a contrast the settled UI clears. Wait for every cell to reach full
// opacity before scanning. (No-op when the countdown isn't rendered.)
async function settleHomeCountdown(page: Page): Promise<void> {
	await page.waitForFunction(() => {
		const cells = Array.from(document.querySelectorAll('.countdown-cell'));
		return cells.every((cell) => getComputedStyle(cell).opacity === '1');
	});
}

// axe scans the *rendered* page, so each scan waits for a stable landmark first —
// analysing mid-boot would flag the splash, not the app. Full WCAG A/AA is
// enforced, color-contrast included.
// Every scan runs in both themes: dark mode's colours are tuned separately
// (app.css), so a pairing that clears AA in light can miss it in dark.
for (const colorScheme of ['light', 'dark'] as const) {
	test.describe(`accessibility (axe), ${colorScheme}`, { tag: '@a11y' }, () => {
		// Emulate reduced motion so entrance animations (the home countdown fades its
		// cells in) are stilled before the scan — axe would otherwise measure a colour
		// mid-fade against its backdrop and flag a contrast the settled UI clears. The
		// app already gates those animations on prefers-reduced-motion.
		//
		// Goes through `contextOptions`, not a top-level `reducedMotion` key: Playwright
		// exposes it on BrowserContextOptions only, so the flat form silently emulates
		// nothing. The config sets no other contextOptions, so nothing is clobbered here.
		test.use({ colorScheme, contextOptions: { reducedMotion: 'reduce' } });

		test('home has no WCAG A/AA violations for a guest', async ({ page, makeAxeBuilder }) => {
			await page.goto('/');
			await expect(page.getByRole('heading', { level: 1, name: 'Главная' })).toBeVisible();
			await settleHomeCountdown(page);

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
			await settleHomeCountdown(page);

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});

		test('the open voting list has no WCAG A/AA violations', async ({
			page,
			api,
			makeAxeBuilder
		}) => {
			api.use({
				'GET /voting/status': json<GetVotingStateOutput>({
					can_vote: true,
					status: 'open',
					voting_start: null,
					voting_end: null
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

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});

		// The per-row vote buttons use the tonal variant, whose tinted fill is the
		// contrast-sensitive part, so the scan runs on a ballot that still offers them.
		test('an open nomination ballot has no WCAG A/AA violations', async ({
			page,
			api,
			makeAxeBuilder
		}) => {
			api.use(loggedInAs());
			api.use({
				'GET /voting/status': json<GetVotingStateOutput>({
					can_vote: true,
					status: 'open',
					voting_start: null,
					voting_end: null
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

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});

		test('the profile hub has no WCAG A/AA violations for a guest', async ({
			page,
			makeAxeBuilder
		}) => {
			await page.goto('/profile');
			await expect(page.getByRole('main').getByRole('link', { name: 'Войти' })).toBeVisible();

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});

		test('the profile hub has no WCAG A/AA violations for an organizer', async ({
			page,
			api,
			makeAxeBuilder
		}) => {
			api.use(organizer());
			await page.goto('/profile');
			await expect(page.getByRole('link', { name: 'Инструменты' })).toBeVisible();

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});

		// The screens mid-festival, where state tints stack: a current event, a cast
		// vote and the player's own leaderboard row each tint their row, and a badge
		// or muted text on that tint is where contrast slips under AA. Default mocks
		// render none of them, so the scans above can't catch it. Same data as the
		// README gallery, clock pinned so its windows are open.
		test.describe('during the festival', () => {
			test.beforeEach(async ({ page, api }) => {
				await page.clock.setFixedTime(GALLERY_NOW);
				api.use({ ...loggedInAs(), ...festivalInProgress });
			});

			test('the schedule with an event on stage has no violations', async ({
				page,
				makeAxeBuilder
			}) => {
				await page.goto('/schedule');
				await expect(page.getByText('Сейчас', { exact: true })).toBeVisible();

				const { violations } = await makeAxeBuilder().analyze();
				expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
			});

			test('a ballot with a cast vote has no violations', async ({ page, makeAxeBuilder }) => {
				await page.goto('/voting/single');
				await expect(page.getByText('Твой голос')).toBeVisible();

				const { violations } = await makeAxeBuilder().analyze();
				expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
			});

			test('the quest leaderboard with the own row has no violations', async ({
				page,
				api,
				makeAxeBuilder
			}) => {
				// The persona the standings mark as the player's own row.
				api.use(loggedInAs({ username: 'ПушистыйПингвин42' }));
				await page.goto('/profile/quest');
				await expect(page.locator('li[aria-current="true"]')).toBeVisible();

				const { violations } = await makeAxeBuilder().analyze();
				expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
			});

			test('notifications with unread items have no violations', async ({
				page,
				api,
				makeAxeBuilder
			}) => {
				api.use({ 'POST /notifications/mark-read': json({}) });
				await page.goto('/notifications');
				await expect(page.getByText('Гардероб работает до 21:00.', { exact: false })).toBeVisible();

				const { violations } = await makeAxeBuilder().analyze();
				expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
			});
		});

		// An error boundary renders no page load, so the navbar has no title; the
		// error card's own title has to be the page's <h1>.
		test('an error page has no violations', async ({ page, api, makeAxeBuilder }) => {
			api.use(loggedInAs());
			await page.goto('/schedule/changes');
			await expect(page.getByRole('heading', { level: 1, name: 'Доступ ограничен' })).toBeVisible();

			const { violations } = await makeAxeBuilder().analyze();
			expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
		});
	});
}
