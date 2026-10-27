import type { Page } from '@playwright/test';

import { expect, test } from '../fixtures';

async function stageWaitingUpdate(page: Page) {
	await page.addInitScript(() => {
		const APPLIED = 'e2e:update-applied';
		const container = new EventTarget();
		const waiting = {
			state: 'installed',
			addEventListener() {},
			postMessage(message: unknown) {
				if (message !== 'skipWaiting') return;
				sessionStorage.setItem(APPLIED, '1');
				setTimeout(() => container.dispatchEvent(new Event('controllerchange')));
			}
		};
		const registration = Object.assign(new EventTarget(), {
			waiting: sessionStorage.getItem(APPLIED) ? null : waiting,
			installing: null,
			update: () => Promise.resolve()
		});
		Object.defineProperty(navigator, 'serviceWorker', {
			configurable: true,
			value: {
				controller: {},
				ready: Promise.resolve(registration),
				register: () => Promise.resolve(registration),
				addEventListener: container.addEventListener.bind(container),
				removeEventListener: container.removeEventListener.bind(container)
			}
		});
	});
}

const waitForUpdateApplied = (page: Page) =>
	page.waitForFunction(() => sessionStorage.getItem('e2e:update-applied') === '1');

test.describe('app update', () => {
	test('marks the Profile tab and offers the update on the hub', async ({ page }) => {
		await stageWaitingUpdate(page);
		await page.goto('/profile');

		await expect(
			page.getByRole('navigation', { name: 'Разделы' }).getByRole('link', { name: /обновление/ })
		).toHaveAccessibleName(/^Профиль/);

		await page.getByRole('button', { name: /Обновить приложение/ }).click();
		await waitForUpdateApplied(page);
		await expect(page.getByRole('button', { name: /Обновить приложение/ })).toHaveCount(0);
	});

	test('applies a waiting update at the next page change', async ({ page }) => {
		await stageWaitingUpdate(page);
		await page.goto('/profile');
		await page.evaluate(() => Object.assign(window, { e2eSamePage: true }));

		await page
			.getByRole('navigation', { name: 'Разделы' })
			.getByRole('link', { name: 'Карта' })
			.click();

		await expect(page).toHaveURL(/\/map$/);
		await waitForUpdateApplied(page);
		await page.waitForFunction(() => !('e2eSamePage' in window));
	});

	test('shows no mark without a waiting update', async ({ page }) => {
		await page.goto('/profile');
		await expect(page.getByRole('main')).toBeVisible();
		await expect(page.getByRole('button', { name: /Обновить приложение/ })).toHaveCount(0);
		await expect(
			page.getByRole('navigation', { name: 'Разделы' }).getByRole('link', { name: /обновление/ })
		).toHaveCount(0);
	});
});
