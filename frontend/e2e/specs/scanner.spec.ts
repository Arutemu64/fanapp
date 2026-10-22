import { fileURLToPath } from 'node:url';

import { expect, loggedInAs, problem, test } from '../fixtures';

// Chromium plays a file as the camera and answers the permission prompt itself
// (https://webrtc.org/getting-started/testing). WebKit has no such switch, so
// playwright.config.ts keeps this file off its project. The frame holds a
// synthetic number, not a real ticket's.
const CAMERA_FEED = fileURLToPath(new URL('../media/ticket-qr.mjpeg', import.meta.url));
const SCANNED_NUMBER = '1234567890123456';

test.use({
	launchOptions: {
		args: [
			'--use-fake-ui-for-media-stream',
			'--use-fake-device-for-media-stream',
			`--use-file-for-fake-video-capture=${CAMERA_FEED}`
		]
	}
});

test('links a ticket scanned with the camera, then turns the camera off', async ({ page, api }) => {
	let sentBarcode: unknown;
	api.use({
		...loggedInAs(),
		'POST /me/ticket': (route) => {
			sentBarcode = (route.request().postDataJSON() as { barcode: string }).barcode;
			return problem('TICKET_NOT_FOUND', 404);
		}
	});
	await page.goto('/profile/ticket');

	await page.getByRole('button', { name: 'Сканировать билет' }).click();
	await expect(page.getByRole('dialog', { name: 'Сканирование билета' })).toBeVisible();

	// A miss still proves the round trip: the decoded number reached the field and
	// the API, and the dialog closed on the first read, taking the camera with it.
	await expect(page.getByRole('dialog')).toHaveCount(0);
	await expect(page.getByLabel('Номер билета')).toHaveValue(SCANNED_NUMBER);
	await expect(page.getByRole('alert')).toHaveText('Билет не найден');
	expect(sentBarcode).toBe(SCANNED_NUMBER);
	await expect(page.locator('video')).toHaveCount(0);
});
