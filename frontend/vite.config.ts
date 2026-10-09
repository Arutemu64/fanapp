import { sentrySvelteKit } from '@sentry/sveltekit';
import adapter from '@sveltejs/adapter-static';
import { enhancedImages } from '@sveltejs/enhanced-img';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';
import Icons from 'unplugin-icons/vite';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

// The whole monorepo shares the single root `.env` (see .env.example); the
// frontend has no env file of its own. `envDir` points Vite's own env loading
// (import.meta.env) at the repo root, and `loadEnv` below does the same for
// this config file itself — Vite deliberately does not inject .env files into
// process.env while the config is being evaluated, so `process.env.X` alone
// would miss values set in the file.
const rootDir = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig(({ mode }) => {
	// Empty prefix = load every variable, not just VITE_*. Only this config
	// reads the result; client exposure stays gated by the PUBLIC_* / VITE_*
	// prefixes. Real environment variables (Docker, CI) win over file values —
	// loadEnv applies process.env last, matching Vite's documented precedence.
	const env = loadEnv(mode, rootDir, '');

	// Everything the build-time source-map upload needs. Deliberately no
	// fallbacks: the instance these values point at is deployment-specific, and a
	// hardcoded default outlives the instance it was written for — an upload
	// aimed at a dead host fails late and confusingly. The prod Docker build
	// supplies all four (SENTRY_AUTH_TOKEN arrives as a BuildKit secret, so it is
	// a real env var, which loadEnv picks up alongside the file values).
	const sentryUpload = {
		org: env.SENTRY_ORG,
		project: env.SENTRY_PROJECT,
		sentryUrl: env.SENTRY_URL,
		authToken: env.SENTRY_AUTH_TOKEN
	};
	// With any part missing (CI, local dev) skip the upload work instead of
	// doing it and then failing to upload.
	const canUploadSourceMaps = Object.values(sentryUpload).every(Boolean);

	return {
		envDir: rootDir,
		// The build's identity, inlined as constants (declared in src/app.d.ts) for
		// the profile footer. Build inputs, not settings: the publish workflow and
		// `just run-prod` pass them as Docker build args, and nothing can change them
		// after the build. Not `$app/env/public`, which fails the build on a declared
		// var the environment lacks, so every .env would need empty placeholders.
		// See docs/dependencies.md "Versioning the app".
		define: {
			__APP_VERSION__: JSON.stringify(env.APP_VERSION ?? ''),
			__APP_BUILD__: JSON.stringify(env.APP_BUILD ?? '')
		},
		plugins: [
			sentrySvelteKit({
				...sentryUpload,
				autoUploadSourceMaps: canUploadSourceMaps,
				release: {
					// Names the release the source maps are uploaded under, and gets
					// injected into the bundle so the SDK reports the same name — see the
					// note in src/hooks.client.ts. The commit SHA, matching the backend's
					// Sentry release. Left undefined (not '') when unset so the plugin's
					// own detection, the git HEAD SHA, still applies on the host.
					name: env.APP_BUILD || undefined
				}
			}),
			tailwindcss(),
			// Processes <enhanced:img> on the map page into AVIF/WebP + resized
			// variants. Returns a Promise<Plugin[]>, which Vite resolves in place;
			// must precede sveltekit().
			enhancedImages(),
			sveltekit({
				// Consult https://svelte.dev/docs/kit/integrations
				// for more information about preprocessors
				preprocess: vitePreprocess(),
				// The whole monorepo shares the single root `.env` (see .env.example) —
				// the frontend has no env file of its own. `$app/env/public` loads
				// from there; real environment variables (Docker build args, CI) still
				// take precedence over the file. Path is relative to the frontend dir,
				// where all commands run (justfile, Docker WORKDIR).
				env: { dir: '..' },
				// SPA build: the app is client-rendered, so there is no server.
				// adapter-static emits a static bundle and a `fallback` page that an
				// NGINX container serves for every unknown route, letting the client
				// router take over. See https://svelte.dev/docs/kit/single-page-apps
				// The service worker precaches this page by name (src/service-worker/).
				adapter: adapter({ fallback: '200.html' }),
				// We register the worker manually (src/lib/utils/serviceWorker.ts) so the
				// register() promise gets a .catch(). SvelteKit's built-in registration
				// doesn't, so a browser that refuses registration (storage-partitioned
				// embeds, private modes) surfaces an uncaught "Error: Rejected" to Sentry.
				serviceWorker: { register: false }
			}),
			Icons({
				compiler: 'svelte'
			})
		],
		optimizeDeps: {
			// The service worker (src/service-worker/) is a separate SvelteKit entry
			// that Vite's initial dep scan doesn't crawl, so these workbox packages get
			// discovered only when /service-worker.js is first requested — triggering a
			// second optimize pass and a full page reload mid-session. Pre-declaring
			// them folds them into the first pass, so the dev server settles once.
			include: [
				'workbox-core',
				'workbox-expiration',
				'workbox-precaching',
				'workbox-routing',
				'workbox-strategies'
			]
		},
		// Tests live here rather than in a vitest.config.ts of their own so they run
		// through the SvelteKit plugin above: that is what resolves `#lib`/`$app`
		// and compiles runes in `*.svelte.test.ts` files. See docs/testing.md.
		test: {
			// Also matches `*.svelte.test.ts`, where runes are available.
			include: ['src/**/*.test.ts'],
			// No DOM: component tests are deliberately out of scope (ADR-0011).
			environment: 'node',
			// Undo vi.spyOn / vi.fn implementations after each test so a mock can't leak into the next.
			restoreMocks: true,
			// Same for vi.stubGlobal (the fake Web Storage in the storage tests).
			unstubGlobals: true,
			// Same for vi.stubEnv.
			unstubEnvs: true
		},
		// Tests exercise browser code, so resolve packages' browser entry points
		// even though the runner is Node. Scoped to test runs so the app build
		// keeps Vite's normal resolution.
		resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
		server: {
			host: true,
			allowedHosts: true,
			// Dev server port. Read from FRONTEND_PORT so a single var drives the port
			// both with Docker (compose passes it in) and without (`just frontend-dev`).
			// Default 3000 to match the documented URL. strictPort fails fast if the
			// port is taken instead of silently drifting to 3001 — the Caddy/vite proxy
			// contract assumes a fixed port, so a silent change would break it.
			port: Number(env.FRONTEND_PORT ?? 3000),
			strictPort: true,
			// In dev the frontend and backend run on different origins, but the app
			// calls the API with a relative base (`PUBLIC_API_URL=/api`). Proxy `/api`
			// to the backend so dev mirrors the same-origin prod setup (Caddy) and
			// needs no CORS. http-proxy streams responses, so SSE (`/api/events`) works.
			proxy: {
				'/api': {
					// Mirror Caddy's `handle_path /api*` — strip the prefix; the backend
					// serves routes at root (uvicorn root_path="/api" is informational).
					target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/api/, '')
				}
			}
		}
	};
});
