import type { Browser, BrowserContextOptions, Page } from '@playwright/test';

import { writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

import type { ListQuestHistoryOutput } from '../../src/lib/api/generated/types.gen';
import type { Handlers } from '../mocks/api';

import { expect, json, loggedInAs, test } from '../fixtures';
import { ApiMock } from '../mocks/api';
import { baselineHandlers } from '../mocks/defaults';
import { installSseDouble } from '../mocks/sse';
import {
	GALLERY_NOW,
	notifications,
	questStanding,
	scheduleEntries,
	singleDefile,
	subscriptions
} from './data';

// One test per README image: the gallery, then the hero. Run with
// `just readme-gallery`, then review the image diff in docs/assets/ before committing.

const OUT_DIR = new URL('../../../docs/assets/readme-gallery/', import.meta.url);
const HEADER_OUT = new URL('../../../docs/assets/readme-header.webp', import.meta.url);
const WEBP_QUALITY = 0.85;

const HOUR_MS = 3_600_000;
const now = GALLERY_NOW.getTime();

// A logged-in visitor during the festival, with voting open and two unread
// notifications for the bell badge. The quest is on, so every signed-in boot
// also saves the score and history for offline (warmOfflineCache): those two
// answer on every screen, not just the quest's.
const visitorAtFestival: Handlers = {
	...loggedInAs({ ticket: null }),
	'GET /config': json({
		festival_start: new Date(now - 2 * HOUR_MS).toISOString(),
		festival_end: new Date(now + 6 * HOUR_MS).toISOString(),
		quest_enabled: true,
		quest_max_award: 100,
		schedule_changeover_seconds: 30
	}),
	'GET /notifications/unread-count': json({ count: 2 }),
	'GET /voting/status': json({
		can_vote: true,
		status: 'open',
		voting_start: new Date(now - HOUR_MS).toISOString(),
		voting_end: new Date(now + 4 * HOUR_MS).toISOString()
	}),
	'GET /schedule/': json({ schedule: scheduleEntries }),
	'GET /schedule/subscriptions/': json({ subscriptions }),
	'GET /voting/nominations/single': json(singleDefile),
	'GET /notifications/': json({ notifications, next_cursor: null }),
	'GET /quest': json(questStanding),
	'GET /quest/history': json<ListQuestHistoryOutput>({ awards: [], next_cursor: null })
};

// Playwright only writes PNG or JPEG, so the browser that took the shot re-encodes
// it: Chromium's canvas encodes WebP (alpha included), which keeps this free of an
// image library.
async function writeWebp(page: Page, png: Buffer, out: URL): Promise<void> {
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
	await writeFile(out, Buffer.from(webpBase64, 'base64'));
}

async function saveWebp(page: Page, name: string): Promise<void> {
	const png = await page.screenshot({ animations: 'disabled', caret: 'hide' });
	await writeWebp(page, png, new URL(`${name}.webp`, OUT_DIR));
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
	await expect(
		page.getByRole('heading', { name: 'Эдвард Элрик — Стальной алхимик' })
	).toBeVisible();
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
	// Opening the page reads everything, so its own bell shows no badge; the
	// items it just read stay flagged new for this visit.
	api.use({
		'GET /notifications/unread-count': json({ count: 0 }),
		'POST /notifications/mark-read': json({})
	});
	await page.goto('/notifications');
	await expect(page.getByText('Гардероб работает до 21:00.', { exact: false })).toBeVisible();
	await settle(page);
	await saveWebp(page, 'notifications');
});

test('map', async ({ page }) => {
	await page.goto('/map');
	await expect(page.getByRole('img', { name: 'Карта 1 этажа' })).toBeVisible();
	await settle(page);
	await saveWebp(page, 'map');
});

test('profile', async ({ page, api }) => {
	// A linked ticket and Telegram fill the hub's values: «Привязан», «Включены»;
	// the quest row shows a balance mid-festival.
	api.use({
		...loggedInAs({
			username: 'ПушистыйПингвин42',
			ticket: { id: 'ticket-1', barcode: '4600000000017', role: 'visitor' },
			social_identities: [{ provider: 'telegram' }]
		})
	});
	await page.goto('/profile');
	await expect(page.getByText('Включены')).toBeVisible();
	await expect(page.getByText('120 баллов')).toBeVisible();
	await settle(page);
	await saveWebp(page, 'profile');
});

test('quest', async ({ page, api }) => {
	api.use(loggedInAs({ username: 'ПушистыйПингвин42' }));
	await page.goto('/profile/quest');
	await expect(page.getByRole('img', { name: 'QR-код игрока @ПушистыйПингвин42' })).toBeVisible();
	await expect(page.getByText('Место')).toBeVisible();
	await settle(page);
	await saveWebp(page, 'quest');
});

// The README hero (docs/assets/readme-header.webp): Home on a laptop and an iPhone,
// framed by device-frames.html. Each device gets its own mocked context, since the
// test's `page` is the gallery's 390px phone. Every option is spelled out because
// browser.newContext() inside a test inherits the project's `use` (isMobile, 1.5×).
const LAPTOP: BrowserContextOptions = {
	viewport: { width: 1280, height: 720 },
	deviceScaleFactor: 1,
	isMobile: false,
	hasTouch: false
};
// iPhone 16 (393×852 pt). 2× rather than its native 3×: the frame shows the phone at
// under 400px wide, so 3× would only add weight.
const IPHONE: BrowserContextOptions = {
	viewport: { width: 393, height: 852 },
	deviceScaleFactor: 2,
	isMobile: true,
	hasTouch: true
};
// Chromium leaves env(safe-area-inset-*) at 0, which would put the navbar under the
// status bar and the nav pill on the home indicator; the CDP override gives the app
// the iPhone 16's real insets. https://useyourloaf.com/blog/iphone-16-screen-sizes/
const IPHONE_INSETS = { top: 59, bottom: 34 };

// The page API device-frames.html defines.
interface DeviceFramesWindow {
	frameScreens(screens: { desktop?: string; phone?: string; title?: string }): Promise<void>;
}

async function captureHome(
	browser: Browser,
	options: BrowserContextOptions,
	insets?: typeof IPHONE_INSETS
): Promise<Buffer> {
	const context = await browser.newContext(options);
	await installSseDouble(context);
	await new ApiMock(context, baselineHandlers).use(visitorAtFestival).install();
	const page = await context.newPage();
	if (insets) {
		const cdp = await context.newCDPSession(page);
		await cdp.send('Emulation.setSafeAreaInsetsOverride', { insets });
	}
	await page.clock.setFixedTime(GALLERY_NOW);
	await page.goto('/');
	await expect(page.getByText('Эдвард Элрик — Стальной алхимик').first()).toBeVisible();
	await settle(page);
	const png = await page.screenshot({ animations: 'disabled', caret: 'hide' });
	await context.close();
	return png;
}

test('header', async ({ browser }, testInfo) => {
	const shots = {
		desktop: await captureHome(browser, LAPTOP),
		phone: await captureHome(browser, IPHONE, IPHONE_INSETS)
	};

	const screens: Record<string, string> = {};
	for (const [screen, png] of Object.entries(shots)) {
		const path = testInfo.outputPath(`${screen}.png`);
		await writeFile(path, png);
		screens[screen] = pathToFileURL(path).href;
	}

	const context = await browser.newContext({
		viewport: { width: 1920, height: 1080 },
		deviceScaleFactor: 1,
		isMobile: false,
		hasTouch: false
	});
	const page = await context.newPage();
	await page.goto(new URL('device-frames.html', import.meta.url).href);
	await page.evaluate(async (urls) => {
		await (window as unknown as DeviceFramesWindow).frameScreens(urls);
	}, screens);
	const png = await page.locator('#stage').screenshot({ omitBackground: true });
	await writeWebp(page, png, HEADER_OUT);
	await context.close();
});
