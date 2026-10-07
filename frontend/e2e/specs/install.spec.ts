import { expect, test } from '../fixtures';

// The install row follows @khmyznikov/pwa-install's own availability signal, so a
// library bump can silently hide it where users need it or show it where nothing
// can be installed. These pin both sides, using user agents the library keys on.
const TELEGRAM_ANDROID =
	'Mozilla/5.0 (Linux; Android 14; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.0.0 Mobile Safari/537.36 Telegram-Android/11.2.2';
const FIREFOX_DESKTOP = 'Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0';

test.use({ locale: 'ru-RU' });

test.beforeEach(async ({ page }) => {
	// The test browser is Chromium/WebKit whatever the user agent says; drop the
	// install APIs a WebView or Firefox lacks, or the library takes Chrome's path.
	await page.addInitScript(() => {
		Reflect.deleteProperty(window, 'BeforeInstallPromptEvent');
		Reflect.deleteProperty(Navigator.prototype, 'install');
	});
});

test.describe('in an Android in-app browser', () => {
	// A messenger WebView is always phone-sized; the library's wide layout renders
	// the how-to steps hidden, so the desktop project would test a case that
	// cannot happen.
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
		await page.goto('/profile');
		await expect(page.getByText('Тема', { exact: true })).toBeVisible();

		// The library's fallback reports availability on a 1 s timer, so give it
		// longer than that before asserting the row never appeared.
		await page.waitForTimeout(2000);
		await expect(page.getByRole('button', { name: /Установить приложение/ })).toHaveCount(0);
	});
});
