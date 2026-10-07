import { defineConfig, devices, webkit } from '@playwright/test';
import { existsSync } from 'node:fs';

// The E2E suite drives `vite preview` of a real production build, never the dev
// server, so it tests the bundle that ships — not dev-only transforms.
const PORT = 4173;
const BASE_URL = `http://127.0.0.1:${PORT}`;

// Chromium is always installed (CI, `playwright install chromium` locally, and the
// web session-start hook). WebKit is opt-in, so the `mobile-webkit` project runs
// wherever it has been installed (`just frontend-e2e-install-webkit`) and is
// skipped elsewhere. CI always runs it: it installs WebKit itself, and a missing
// browser there must fail the job rather than silently drop the project.
// `executablePath()` is where Playwright expects its bundled build for
// this exact version, so a stale WebKit from an older pin reads as not installed.
function runWebkit(): boolean {
	if (process.env.CI) return true;
	return existsSync(webkit.executablePath());
}

export default defineConfig({
	testDir: './e2e/specs',
	tsconfig: './e2e/tsconfig.json',
	// Each spec file is isolated (fresh context) and safe to run in parallel: the
	// backend is mocked per-test, so nothing is shared between them.
	fullyParallel: true,
	// One worker on CI, per https://playwright.dev/docs/ci: stability and
	// reproducibility over speed on a shared runner. Locally, half the cores.
	workers: process.env.CI ? 1 : undefined,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
	use: {
		baseURL: BASE_URL,
		trace: 'on-first-retry',
		// Capture a screenshot when a test fails; the HTML reporter embeds it, so a
		// red CI run is debuggable from the uploaded report alone.
		screenshot: 'only-on-failure'
	},
	// Build once, then serve the static build. The build reads the root .env
	// (vite `envDir`), which a web session's session-start hook seeds/backfills.
	webServer: {
		command: `pnpm build && pnpm preview --port ${PORT} --strictPort`,
		url: BASE_URL,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000
	},
	projects: [
		{
			// Mobile-first app → a phone viewport is the primary surface under test.
			name: 'mobile-chromium',
			use: { ...devices['Pixel 7'] }
		},
		{
			// Desktop viewport catches layout that only appears on the wide breakpoint
			// (the sidebar shell instead of the bottom nav).
			name: 'desktop-chromium',
			use: { ...devices['Desktop Chrome'] }
		},
		// iOS Safari (WebKit) is the app's real primary surface — it is mobile-first
		// and its audience is largely on iPhones — and the one engine Chromium can't
		// stand in for.
		...(runWebkit()
			? [
					{
						name: 'mobile-webkit',
						use: { ...devices['iPhone 14'] }
					}
				]
			: [])
	]
});
