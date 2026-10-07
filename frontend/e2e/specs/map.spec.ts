import type { Page } from '@playwright/test';

import { expect, test } from '../fixtures';

async function openFirstMap(page: Page) {
	await page.goto('/map');
	await page
		.getByRole('button', { name: /Открыть карту на весь экран/ })
		.first()
		.click();
	const viewer = page.getByRole('dialog', { name: 'Просмотр карты' });
	await expect(viewer).toBeVisible();
	return viewer;
}

test.describe('map viewer', () => {
	test('the back gesture closes the viewer and stays on the map page', async ({ page }) => {
		const viewer = await openFirstMap(page);

		await page.goBack();

		await expect(viewer).toHaveCount(0);
		await expect(page).toHaveURL('/map');
	});

	test('offers a single-pointer zoom and the original file to download', async ({ page }) => {
		const viewer = await openFirstMap(page);

		// Pinch is a multipoint gesture, so WCAG 2.5.1 needs a single-pointer way in.
		await viewer.getByRole('button', { name: 'Масштаб' }).click();
		await expect(page.locator('.pswp')).toHaveClass(/pswp--zoomed-in/);

		const download = viewer.getByRole('link', { name: 'Скачать карту' });
		await expect(download).toHaveAttribute('download', 'map_1.png');
		await expect(download).toHaveAttribute('href', /\.png$/);
	});

	test.describe('with the opening animation stilled', () => {
		// PhotoSwipe ignores its close button until the opening animation ends;
		// under reduced motion it opens instantly, so the click is never swallowed.
		// Through contextOptions: Playwright exposes reducedMotion only there.
		test.use({ contextOptions: { reducedMotion: 'reduce' } });

		test('closing from the viewer drops its history entry', async ({ page }) => {
			await page.goto('/');
			const viewer = await openFirstMap(page);

			await viewer.getByRole('button', { name: 'Закрыть' }).click();
			await expect(viewer).toHaveCount(0);

			// One step back now leaves the map page: the viewer's entry is already gone.
			await page.goBack();
			await expect(page).toHaveURL('/');
		});
	});
});
