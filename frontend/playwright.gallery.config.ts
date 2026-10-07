import { defineConfig } from '@playwright/test';

import baseConfig from './playwright.config';

// Captures the README screenshot gallery (`just readme-gallery`), not a test run:
// the specs write docs/assets/readme-gallery/*.webp. Kept out of the E2E suite's
// testDir so `just frontend-e2e` never rewrites committed images.
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
				// A 390×844 phone (iPhone 12–14) at 1.5× gives the 585×1266 images the
				// README shows at 195px wide, sharp on a 3× display without the file
				// weight of a native 3× capture.
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
