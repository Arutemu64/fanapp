import type { Page } from '@playwright/test';

import type { ScheduleDto } from '../../src/lib/api/generated/types.gen';

import { expect, json, loggedInAs, organizer, test } from '../fixtures';

const isDesktop = (projectName: string) => projectName === 'desktop-chromium';

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

const longSchedule: ScheduleDto['schedule'] = [
	{ type: 'block_start', id: 'block-1', title: 'Блок 1' },
	...Array.from({ length: 60 }, (_, index) => ({
		type: 'event' as const,
		id: `event-${index + 1}`,
		number: index + 1,
		title: `Выступление ${index + 1}`,
		duration_seconds: 180,
		is_skipped: false,
		nomination_title: 'Одиночное дефиле',
		position: index + 1
	}))
];

test.describe('native feel', () => {
	test('hides the top bar on scroll and keeps a tab where it was left', async ({
		page,
		api
	}, testInfo) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, schedule: longSchedule })
		});
		await page.goto('/schedule');
		await expect(page.getByText('Выступление 60')).toBeAttached();
		const title = page.getByRole('heading', { level: 1, name: 'Программа' });
		await expect(title).toBeInViewport();
		await page.evaluate(() => window.scrollBy(0, 1500));
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(1000);
		/* eslint-disable playwright/no-conditional-in-test, playwright/no-conditional-expect -- the desktop shell keeps its bar; each device project takes one branch */
		if (isDesktop(testInfo.project.name)) {
			await expect(title).toBeInViewport();
		} else {
			await expect(title).not.toBeInViewport();
		}
		/* eslint-enable playwright/no-conditional-in-test, playwright/no-conditional-expect */
		await page
			.getByRole('link', { name: /^Открыть уведомления/ })
			.evaluate((link: HTMLElement) => link.focus({ preventScroll: true }));
		await expect(title).toBeInViewport();
		const scrolledTo = await page.evaluate(() => window.scrollY);

		const tabs = page.getByRole('navigation', { name: 'Разделы' });
		await tabs.getByRole('link', { name: 'Карта' }).click();
		await expect(page).toHaveURL('/map');
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

		await tabs.getByRole('link', { name: 'Программа' }).click();
		await expect(page).toHaveURL('/schedule');
		await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scrolledTo);
		await expect(title).toBeInViewport();
	});

	test('reopens a tab with the filters it was left with', async ({ page, api }) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, schedule: longSchedule })
		});
		await page.goto('/schedule');
		const search = page.getByRole('searchbox', { name: 'Поиск по программе' });

		await search.fill('Выступление 5');
		await expect(page).toHaveURL((url) => url.searchParams.get('q') === 'Выступление 5');

		const tabs = page.getByRole('navigation', { name: 'Разделы' });
		await tabs.getByRole('link', { name: 'Карта' }).click();
		await expect(page).toHaveURL('/map');
		await tabs.getByRole('link', { name: 'Программа' }).click();

		await expect(search).toHaveValue('Выступление 5');
		await expect(page.getByText('Выступление 4', { exact: true })).toBeHidden();
	});

	test('the back arrow returns to the tab with its filters', async ({ page, api }) => {
		api.use({
			...organizer(),
			'GET /schedule': json({ current_event_id: null, schedule: longSchedule }),
			'GET /schedule/changes': json({ schedule_changes: [], next_cursor: null })
		});
		await page.goto('/schedule?q=Выступление+5');

		await page.getByRole('link', { name: 'Изменения программы' }).click();
		await expect(page).toHaveURL('/schedule/changes');
		await page.getByRole('link', { name: 'Назад к программе' }).click();

		await expect(page).toHaveURL((url) => url.searchParams.get('q') === 'Выступление 5');
		await expect(page.getByRole('searchbox', { name: 'Поиск по программе' })).toHaveValue(
			'Выступление 5'
		);
	});

	test('forgets the tabs’ filters on logout', async ({ page, api }) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, schedule: longSchedule }),
			'POST /auth/logout': json({})
		});
		await page.goto('/schedule?q=Выступление+5');
		const tabs = page.getByRole('navigation', { name: 'Разделы' });
		await expect(tabs.getByRole('link', { name: 'Программа' })).toHaveAttribute('href', /q=/);

		await tabs.getByRole('link', { name: 'Профиль' }).click();
		await page.getByRole('main').getByRole('button', { name: 'Выйти' }).click();
		await page
			.getByRole('alertdialog', { name: 'Выйти из аккаунта?' })
			.getByRole('button', { name: 'Выйти' })
			.click();
		await expect(page).toHaveURL('/');

		await tabs.getByRole('link', { name: 'Программа' }).click();
		await expect(page).toHaveURL('/schedule');
		await expect(page.getByRole('searchbox', { name: 'Поиск по программе' })).toHaveValue('');
	});

	test('keeps a focused control clear of the bars', async ({ page, api }) => {
		api.use({
			...loggedInAs(),
			'GET /schedule': json({ current_event_id: null, schedule: longSchedule })
		});
		await page.goto('/schedule');
		await expect(page.getByText('Выступление 60')).toBeAttached();

		await focusAndExpectUnobscured(page, 'event-30', 20);
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
			.getByRole('link', { name: 'Карта' })
			.click();
		await expect(page).toHaveURL('/map');

		/* eslint-disable playwright/no-conditional-in-test -- the expectation is per device project and browser support */
		const expected =
			supported && !isDesktop(testInfo.project.name) ? ['forward', 'back', 'fade'] : [];
		/* eslint-enable playwright/no-conditional-in-test */
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
		await dialog.evaluate((element) =>
			Promise.allSettled(element.getAnimations().map((animation) => animation.finished))
		);
		const box = await dialog.boundingBox();
		const viewport = page.viewportSize();
		expect(box).not.toBeNull();
		expect(viewport).not.toBeNull();

		/* eslint-disable playwright/no-conditional-in-test, playwright/no-conditional-expect -- the null guard only narrows the types; the layout differs per device project by design */
		if (box === null || viewport === null) return;
		if (isDesktop(testInfo.project.name)) {
			expect(Math.abs(box.x + box.width / 2 - viewport.width / 2)).toBeLessThan(2);
			expect(Math.abs(box.y + box.height / 2 - viewport.height / 2)).toBeLessThan(2);
		} else {
			expect(box.width).toBe(viewport.width);
			expect(Math.round(box.y + box.height)).toBe(viewport.height);
		}
		/* eslint-enable playwright/no-conditional-in-test, playwright/no-conditional-expect */
	});
});
