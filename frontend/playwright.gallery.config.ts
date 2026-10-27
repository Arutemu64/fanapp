import { defineConfig } from '@playwright/test';

import baseConfig from './playwright.config';

export default defineConfig({
	...baseConfig,
	testDir: './e2e/gallery',
	retries: 0,
	reporter: [['list']],
	use: { ...baseConfig.use, trace: 'off', screenshot: 'off' },
	projects: [
		{
			name: 'gallery',
			use: {
				browserName: 'chromium',
				viewport: { width: 390, height: 844 },
				deviceScaleFactor: 1.5,
				isMobile: true,
				hasTouch: true,
				colorScheme: 'light',
				locale: 'ru-RU',
				timezoneId: 'Europe/Moscow'
			}
		}
	]
});
