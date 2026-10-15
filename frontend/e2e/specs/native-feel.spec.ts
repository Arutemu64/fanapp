import type { Page } from '@playwright/test';

import type { GetScheduleOutput } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, test } from '../fixtures';

// The phone-only "native feel" layer: page transitions and the bottom-sheet dialog. Each check
// also pins that the desktop project keeps the plain behaviour.

const isDesktop = (projectName: string) => projectName === 'desktop-chromium';

// Records every value html[data-nav-transition] takes, so a test can read which
// transitions ran after the fact without racing their 250ms animations.
async function recordTransitions(page: Page) {
	await page.evaluate(() => {
		const kinds: string[] = [];
		Object.assign(window, { __navTransitions: kinds });
		new MutationObserver(() => {
			const kind = document.documentElement.dataset.navTransition;
			if (kind) kinds.push(kind);
		}).observe(document.documentElement, { attributes: true });
	});
}

async function recordedTransitions(page: Page): Promise<string[]> {
	return page.evaluate(
		() => (window as unknown as { __navTransitions: string[] }).__navTransitions
	);
}

async function openEditProfile(page: Page) {
	await page.goto('/profile/account');
	await page.getByRole('button', { name: 'Редактировать' }).click();
	const dialog = page.getByRole('dialog');
	await expect(dialog).toBeVisible();
	return dialog;
}

// Parks the row's first control at `offset` px from the top of the viewport (under a
// bar), focuses it, and checks that focus scrolled it out from under: the control
// itself is the topmost element at its top and bottom edge. Focusing a control that
// sits off-screen proves nothing, since browsers centre it.
async function focusAndExpectUnobscured(page: Page, eventId: string, offset: number) {
	const control = page.locator(`[data-event-id="${eventId}"] button`).first();
	await control.evaluate((element, offset) => {
		window.scrollBy(0, element.getBoundingClientRect().top - offset);
	}, offset);
	await control.focus();
	await expect
		.poll(() =>
			control.evaluate((element) => {
				const box = element.getBoundingClientRect();
				const x = box.left + box.width / 2;
				const edges = [box.top + 1, box.bottom - 1];
				return edges.every((y) => element.contains(document.elementFromPoint(x, y)));
			})
		)
		.toBe(true);
}

// Long enough that the page scrolls well past the top bar on any project's viewport.
const longSchedule: GetScheduleOutput['schedule'] = [
	{ type: 'block_start', id: 'block-1', title: 'Блок 1', order: 0 },
	...Array.from({ length: 60 }, (_, index) => ({
		type: 'event' as const,
		id: `event-${index + 1}`,
		number: index + 1,
		title: `Выступление ${index + 1}`,
		duration: 180,
		order: index + 1,
		is_current: false,
		is_skipped: false,
		nomination_title: 'Одиночное дефиле',
		position: index + 1
	}))
];

test.describe('native feel', () => {
	// The document is the scroll region: SvelteKit restores it on back/forward, and the
	// shell adds the tab-bar convention of returning a re-entered tab to where it was left.
	test('hides the top bar on scroll and keeps a tab where it was left', async ({
		page,
		api
	}, testInfo) => {
		api.use({ ...loggedInAs(), 'GET /schedule/': json({ schedule: longSchedule }) });
		await page.goto('/schedule');
		await expect(page.getByText('Выступление 60')).toBeAttached();
		const title = page.getByRole('heading', { level: 1, name: 'Программа' });
		await expect(title).toBeInViewport();
		// Not mouse.wheel: Playwright doesn't support it in mobile WebKit. A scrollBy fires
		// the same `scroll` events the shell's hide-on-scroll listens to.
		await page.evaluate(() => window.scrollBy(0, 1500));
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);
		if (isDesktop(testInfo.project.name)) {
			await expect(title).toBeInViewport();
		} else {
			await expect(title).not.toBeInViewport();
		}
		const scrolledTo = await page.evaluate(() => window.scrollY);

		const tabs = page.getByRole('navigation', { name: 'Разделы' });
		await tabs.getByRole('link', { name: 'Гид' }).click();
		await expect(page).toHaveURL('/guide');
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

		await tabs.getByRole('link', { name: 'Программа' }).click();
		await expect(page).toHaveURL('/schedule');
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scrolledTo);
		// A programmatic restore is no scroll gesture: the bar comes back with the page.
		await expect(title).toBeInViewport();
	});

	// WCAG 2.4.11: a control that keyboard focus scrolls into view must not land under
	// the top chrome, the schedule's sticky headers or the floating bottom nav.
	test('keeps a focused control clear of the bars', async ({ page, api }) => {
		api.use({ ...loggedInAs(), 'GET /schedule/': json({ schedule: longSchedule }) });
		await page.goto('/schedule');
		await expect(page.getByText('Выступление 60')).toBeAttached();

		// Under the top chrome and the schedule's sticky headers.
		await focusAndExpectUnobscured(page, 'event-30', 20);
		// Under the floating bottom nav (phones) or at the bottom edge (desktop).
		const viewportHeight = page.viewportSize()?.height ?? 0;
		await focusAndExpectUnobscured(page, 'event-40', viewportHeight - 30);
	});

	test('slides down and up the hierarchy and fades between tabs, on phones only', async ({
		page,
		api
	}, testInfo) => {
		api.use(loggedInAs());
		await page.goto('/profile');
		await expect(page.getByRole('heading', { level: 1, name: 'Профиль' })).toBeVisible();
		const supported = await page.evaluate(() => 'startViewTransition' in document);
		await recordTransitions(page);

		await page.getByRole('main').getByRole('link', { name: /Билет/ }).click();
		await expect(page).toHaveURL('/profile/ticket');
		await page.getByRole('link', { name: 'Назад в профиль' }).click();
		await expect(page).toHaveURL('/profile');
		await page
			.getByRole('navigation', { name: 'Разделы' })
			.getByRole('link', { name: 'Гид' })
			.click();
		await expect(page).toHaveURL('/guide');

		const expected =
			supported && !isDesktop(testInfo.project.name) ? ['forward', 'back', 'fade'] : [];
		await expect.poll(() => recordedTransitions(page)).toEqual(expected);
		await expect
			.poll(() => page.evaluate(() => document.documentElement.dataset.navTransition))
			.toBeUndefined();
	});

	test('lays a dialog out as a bottom sheet on phones and centred on desktop', async ({
		page,
		api
	}, testInfo) => {
		api.use(loggedInAs());
		const dialog = await openEditProfile(page);
		// Let the enter animation (a CSS keyframe slide/zoom) settle before measuring.
		// allSettled, not all: a cancelled animation rejects `finished`.
		await dialog.evaluate((element) =>
			Promise.allSettled(element.getAnimations().map((animation) => animation.finished))
		);
		const box = (await dialog.boundingBox())!;
		const viewport = page.viewportSize()!;

		if (isDesktop(testInfo.project.name)) {
			expect(Math.abs(box.x + box.width / 2 - viewport.width / 2)).toBeLessThan(2);
			expect(Math.abs(box.y + box.height / 2 - viewport.height / 2)).toBeLessThan(2);
		} else {
			expect(box.width).toBe(viewport.width);
			expect(Math.round(box.y + box.height)).toBe(viewport.height);
		}
	});
});
