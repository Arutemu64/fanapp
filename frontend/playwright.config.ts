import { defineConfig, devices, webkit } from '@playwright/test';
import { existsSync } from 'node:fs';

const PORT = 4173;
const BASE_URL = `http://127.0.0.1:${PORT}`;

const isPullRequest = process.env.GITHUB_EVENT_NAME === 'pull_request';

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
		serviceWorkers: 'block',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure'
	},
	webServer: {
		command: `pnpm build && pnpm preview --config e2e/preview.config.ts --host 127.0.0.1 --port ${PORT} --strictPort`,
		url: `${BASE_URL}/200.html`,
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
			grepInvert: isPullRequest ? /@desktop-only\b/ : undefined,
			use: { ...devices['Pixel 7'] }
		},
		{
			name: 'desktop-chromium',
			grep: isPullRequest ? /@(desktop|desktop-only|smoke|a11y)(?:\s|$)/ : undefined,
			grepInvert: isPullRequest ? /@mobile-chromium-only\b/ : undefined,
			use: { ...devices['Desktop Chrome'] }
		},
		...(runWebkit()
			? [
					{
						name: 'mobile-webkit',
						grepInvert: isPullRequest ? /@(desktop-only|mobile-chromium-only)\b/ : undefined,
						use: { ...devices['iPhone 14'] },
						testIgnore: 'scanner.spec.ts'
					}
				]
			: [])
	]
});
