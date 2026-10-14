import { expect, test } from '../fixtures';

// A real deploy can't be staged under `vite preview`, so these swap
// navigator.serviceWorker for a double whose registration already holds a
// waiting worker. Posting `skipWaiting` to it fires `controllerchange`, as the
// real worker does once it takes over, and records the hand-off in
// sessionStorage so the reloaded page boots with nothing waiting.
async function stageWaitingUpdate(page: import('@playwright/test').Page) {
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

const wasApplied = (page: import('@playwright/test').Page) =>
	page.evaluate(() => sessionStorage.getItem('e2e:update-applied'));

test.describe('app update', () => {
	test('marks the Profile tab and offers the update on the hub', async ({ page }) => {
		await stageWaitingUpdate(page);
		await page.goto('/profile');

		await expect(
			page.getByRole('navigation', { name: 'Разделы' }).getByRole('link', { name: /обновление/ })
		).toHaveAccessibleName(/^Профиль/);

		await page.getByRole('button', { name: /Обновить приложение/ }).click();
		await expect.poll(() => wasApplied(page)).toBe('1');
		await expect(page.getByRole('button', { name: /Обновить приложение/ })).toHaveCount(0);
	});

	test('applies a waiting update at the next page change', async ({ page }) => {
		await stageWaitingUpdate(page);
		await page.goto('/profile');
		// Survives a client-side navigation, not a full load.
		await page.evaluate(() => Object.assign(window, { e2eSamePage: true }));

		await page
			.getByRole('navigation', { name: 'Разделы' })
			.getByRole('link', { name: 'Карта' })
			.click();

		await expect(page).toHaveURL(/\/map$/);
		await expect.poll(() => wasApplied(page)).toBe('1');
		expect(await page.evaluate(() => 'e2eSamePage' in window)).toBe(false);
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
