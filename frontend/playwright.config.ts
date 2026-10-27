import { defineConfig, devices, webkit } from '@playwright/test';
import { existsSync } from 'node:fs';

const PORT = 4173;
const BASE_URL = `http://127.0.0.1:${PORT}`;

function runWebkit(): boolean {
	if (process.env.CI) return true;
	return existsSync(webkit.executablePath());
}

export default defineConfig({
	testDir: './e2e/specs',
	tsconfig: './e2e/tsconfig.json',
	fullyParallel: true,
	workers: process.env.CI ? 2 : undefined,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
	use: {
		baseURL: BASE_URL,
		trace: 'on-first-retry',
		screenshot: 'only-on-failure'
	},
	webServer: {
		command: `pnpm build && pnpm preview --port ${PORT} --strictPort`,
		url: BASE_URL,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000,
		env: {
			PUBLIC_SENTRY_DSN: '',
			PUBLIC_UMAMI_SCRIPT_URL: '',
			APP_VERSION: '1.0.0',
			APP_BUILD: '0123456789abcdef0123456789abcdef01234567'
		}
	},
	projects: [
		{
			name: 'mobile-chromium',
			use: { ...devices['Pixel 7'] }
		},
		{
			name: 'desktop-chromium',
			use: { ...devices['Desktop Chrome'] }
		},
		...(runWebkit()
			? [
					{
						name: 'mobile-webkit',
						use: { ...devices['iPhone 14'] },
						testIgnore: 'scanner.spec.ts'
					}
				]
			: [])
	]
});
