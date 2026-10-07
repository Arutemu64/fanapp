import type { Page } from '@playwright/test';

import { writeFile } from 'node:fs/promises';

import type { Handlers } from '../mocks/api';

import { expect, json, loggedInAs, test } from '../fixtures';
import { GALLERY_NOW, notifications, schedule, singleDefile, subscriptions } from './data';

// One test per README gallery image. Run with `just readme-gallery`, then review
// the diff of docs/assets/readme-gallery/ before committing.

const OUT_DIR = new URL('../../../docs/assets/readme-gallery/', import.meta.url);
const WEBP_QUALITY = 0.85;

const HOUR_MS = 3_600_000;
const now = GALLERY_NOW.getTime();

// A logged-in visitor during the festival, with voting open and two unread
// notifications for the bell badge.
const visitorAtFestival: Handlers = {
	...loggedInAs({ ticket: null }),
	'GET /config': json({
		festival_start: new Date(now - 2 * HOUR_MS).toISOString(),
		festival_end: new Date(now + 6 * HOUR_MS).toISOString()
	}),
	'GET /notifications/unread-count': json({ count: 2 }),
	'GET /voting/status': json({
		can_vote: true,
		status: 'open',
		voting_start: new Date(now - HOUR_MS).toISOString(),
		voting_end: new Date(now + 4 * HOUR_MS).toISOString()
	}),
	'GET /schedule/': json({ schedule }),
	'GET /schedule/subscriptions/': json({ subscriptions }),
	'GET /voting/nominations/single': json(singleDefile),
	'GET /notifications/': json({ notifications })
};

// Playwright only writes PNG or JPEG, so the browser that took the shot re-encodes
// it: Chromium's canvas encodes WebP, which keeps this free of an image library.
async function saveWebp(page: Page, name: string): Promise<void> {
	const png = await page.screenshot({ animations: 'disabled', caret: 'hide' });
	const webpBase64 = await page.evaluate(
		async ({ pngBase64, quality }) => {
			const bitmap = await createImageBitmap(
				await (await fetch(`data:image/png;base64,${pngBase64}`)).blob()
			);
			const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
			canvas.getContext('2d')?.drawImage(bitmap, 0, 0);
			const webp = await canvas.convertToBlob({ type: 'image/webp', quality });
			const bytes = new Uint8Array(await webp.arrayBuffer());
			let binary = '';
			for (const byte of bytes) binary += String.fromCharCode(byte);
			return btoa(binary);
		},
		{ pngBase64: png.toString('base64'), quality: WEBP_QUALITY }
	);
	await writeFile(new URL(`${name}.webp`, OUT_DIR), Buffer.from(webpBase64, 'base64'));
}

async function settle(page: Page): Promise<void> {
	await page.evaluate(() => document.fonts.ready);
	await page.waitForLoadState('networkidle');
}

test.beforeEach(async ({ page, api }) => {
	await page.clock.setFixedTime(GALLERY_NOW);
	api.use(visitorAtFestival);
});

test('schedule', async ({ page }) => {
	await page.goto('/schedule');
	await expect(page.getByText('Эдвард Элрик — Стальной алхимик')).toBeVisible();
	await settle(page);
	await saveWebp(page, 'schedule');
});

test('voting', async ({ page }) => {
	await page.goto('/voting/single');
	await expect(page.getByText('Твой голос')).toBeVisible();
	await settle(page);
	await saveWebp(page, 'voting');
});

test('notifications', async ({ page, api }) => {
	// Opening the page reads everything, so its own bell shows no badge.
	api.use({ 'GET /notifications/unread-count': json({ count: 0 }) });
	await page.goto('/notifications');
	await expect(page.getByText('Гардероб работает до 21:00.', { exact: false })).toBeVisible();
	await settle(page);
	await saveWebp(page, 'notifications');
});

test('map', async ({ page }) => {
	await page.goto('/map');
	// The thumbnails are decorative (alt=""): each card's button carries the name.
	await expect(
		page.getByRole('button', { name: /открыть карту на весь экран/ }).first()
	).toBeVisible();
	await settle(page);
	await saveWebp(page, 'map');
});
