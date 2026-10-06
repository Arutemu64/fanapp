import type { Page } from '@playwright/test';

import { expect, loggedInAs, test } from '../fixtures';

// The phone-only "native feel" layer: page transitions, the bottom-sheet dialog and
// its swipe-to-dismiss, the bottom nav stepping aside for the keyboard. Each check
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

// A touch drag via CDP — Playwright's touchscreen API only taps.
async function touchDrag(page: Page, x: number, y: number, distance: number, steps: number) {
	const cdp = await page.context().newCDPSession(page);
	await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
	for (let step = 1; step <= steps; step++) {
		await cdp.send('Input.dispatchTouchEvent', {
			type: 'touchMove',
			touchPoints: [{ x, y: y + (distance * step) / steps }]
		});
	}
	await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}

async function openEditProfile(page: Page) {
	await page.goto('/profile/account');
	await page.getByRole('button', { name: 'Редактировать' }).click();
	const dialog = page.getByRole('dialog');
	await expect(dialog).toBeVisible();
	return dialog;
}

test.describe('native feel', () => {
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
		// Let the enter animation settle before measuring.
		await expect.poll(async () => (await dialog.boundingBox())?.y).toBeGreaterThan(0);
		await page.waitForTimeout(300);
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

	test('hides the bottom nav while a text field has focus', async ({ page, api }, testInfo) => {
		test.skip(isDesktop(testInfo.project.name), 'the bottom nav is phone-only');
		api.use(loggedInAs());
		const dialog = await openEditProfile(page);
		const nav = page.getByRole('navigation', { name: 'Разделы' });

		await dialog.getByRole('textbox').first().focus();
		await expect(nav).toBeHidden();
		await dialog.getByRole('textbox').first().blur();
		await expect(nav).toBeVisible();
	});

	test('a swipe down dismisses the sheet; a short drag snaps back', async ({
		page,
		api,
		browserName
	}, testInfo) => {
		test.skip(isDesktop(testInfo.project.name), 'the sheet is phone-only');
		test.skip(browserName !== 'chromium', 'touch drags are dispatched over CDP');
		api.use(loggedInAs());
		const dialog = await openEditProfile(page);
		await page.waitForTimeout(300);
		const box = (await dialog.boundingBox())!;
		const x = box.x + box.width / 2;
		const y = box.y + 40;

		await touchDrag(page, x, y, 30, 5);
		await page.waitForTimeout(300);
		await expect(dialog).toBeVisible();
		expect(Math.round((await dialog.boundingBox())!.y)).toBe(Math.round(box.y));

		await touchDrag(page, x, y, 300, 10);
		await expect(dialog).toBeHidden();
	});
});
