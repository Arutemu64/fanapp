import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

// The app is a client-rendered SPA whose service worker and offline behaviour are
// active ONLY in a production build — `vite dev` disables the SW (see
// vite.config.ts `devOptions.enabled: false` and docs/frontend.md §2). So the E2E
// suite drives `vite preview` of a real build, never the dev server, or the whole
// PWA / offline surface would go untested.
const PORT = 4173;
const BASE_URL = `http://127.0.0.1:${PORT}`;

// Zero browser install in a Claude Code web session: the environment pre-bakes a
// Playwright-managed Chromium and exposes a stable `chromium` symlink under
// $PLAYWRIGHT_BROWSERS_PATH. Pointing at it directly means a session runs the
// suite with no `playwright install`, and keeps working even if the baked build
// later drifts from the pinned @playwright/test (the symlink follows it). On CI
// and local machines the variable is unset, so Playwright resolves the browser it
// installed itself. See docs/claude-cloud.md and docs/testing.md.
function prebakedChromium(): string | undefined {
	const base = process.env.PLAYWRIGHT_BROWSERS_PATH;
	if (!base) return undefined;
	const symlink = join(base, 'chromium');
	return existsSync(symlink) ? symlink : undefined;
}

export default defineConfig({
	testDir: './e2e/specs',
	tsconfig: './e2e/tsconfig.json',
	// Each spec file is isolated (fresh context) and safe to run in parallel: the
	// backend is mocked per-test, so nothing is shared between them.
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
	use: {
		baseURL: BASE_URL,
		trace: 'on-first-retry'
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
			// Mobile-first app → a phone viewport is the default surface under test.
			name: 'mobile-chromium',
			use: {
				...devices['Pixel 7'],
				launchOptions: { executablePath: prebakedChromium() }
			}
		}
	]
});
