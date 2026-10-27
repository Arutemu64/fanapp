import { expect, test } from '../fixtures';

const TELEGRAM_ANDROID =
	'Mozilla/5.0 (Linux; Android 14; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.0.0 Mobile Safari/537.36 Telegram-Android/11.2.2';
const FIREFOX_DESKTOP = 'Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0';

test.use({ locale: 'ru-RU' });

test.beforeEach(async ({ page }) => {
	await page.addInitScript(() => {
		Reflect.deleteProperty(window, 'BeforeInstallPromptEvent');
		Reflect.deleteProperty(Navigator.prototype, 'install');
	});
});

test.describe('in an Android in-app browser', () => {
	test.use({ userAgent: TELEGRAM_ANDROID, viewport: { width: 412, height: 915 } });

	test('offers install and explains how to leave the WebView', async ({ page }) => {
		await page.goto('/profile');

		await page.getByRole('button', { name: /Установить приложение/ }).click();
		const dialog = page.locator('pwa-install');
		await dialog.getByRole('button', { name: 'Установить', exact: true }).click();
		await expect(dialog.getByText('Откройте меню встроенного браузера')).toBeVisible();
	});
});

test.describe('in a desktop browser that cannot install', () => {
	test.use({ userAgent: FIREFOX_DESKTOP });

	test('hides the install row', async ({ page }) => {
		await page.clock.install();
		await page.goto('/profile');
		await expect(page.getByText('Тема', { exact: true })).toBeVisible();

		await page.clock.runFor(2000);
		await expect(page.getByRole('button', { name: /Установить приложение/ })).toHaveCount(0);
	});
});
