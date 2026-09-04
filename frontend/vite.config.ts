import { sentrySvelteKit } from '@sentry/sveltekit';
import { enhancedImages } from '@sveltejs/enhanced-img';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { SvelteKitPWA } from '@vite-pwa/sveltekit';
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
		plugins: [
			sentrySvelteKit({
				...sentryUpload,
				autoUploadSourceMaps: canUploadSourceMaps,
				release: {
					// Names the release the source maps are uploaded under, and gets
					// injected into the bundle so the SDK reports the same name — see the
					// note in src/hooks.client.ts. Left undefined (not '') when unset so
					// the plugin's own detection, the git HEAD SHA, still applies.
					name: env.SENTRY_RELEASE || undefined
				}
			}),
			tailwindcss(),
			// Processes <enhanced:img> on the map page into AVIF/WebP + resized
			// variants. Returns a Promise<Plugin[]>, which Vite resolves in place;
			// must precede sveltekit().
			enhancedImages(),
			sveltekit(),
			// injectManifest strategy: SvelteKit compiles our hand-written SW
			// (src/service-worker.ts), then vite-pwa runs Workbox over the built output
			// to generate the precache manifest and inject it at `self.__WB_MANIFEST`.
			// We keep the SW — push, update handshake, API bypass, image runtime cache —
			// and only offload precache assembly + cache versioning to Workbox.
			// `filename` stays the SvelteKit default so the emitted worker remains
			// /service-worker.js (registered by $lib/utils/serviceWorker.ts) and
			// `manifest: false` keeps static/manifest.json as the web app manifest.
			SvelteKitPWA({
				strategies: 'injectManifest',
				srcDir: 'src',
				filename: 'service-worker.js',
				manifest: false,
				injectRegister: false,
				// SPA (adapter-static fallback): include the fallback page in the
				// precache manifest so navigations resolve offline. adapterFallback
				// mirrors svelte.config.js's `fallback: '200.html'`.
				kit: {
					spa: true,
					adapterFallback: '200.html'
				},
				injectManifest: {
					// Precache the app shell. Exclude the content-hashed responsive image
					// variants <enhanced:img> emits (served cache-first at runtime in sw.ts
					// instead — precaching every width/format at install is wasteful and
					// discouraged: https://developer.chrome.com/docs/workbox/precaching-dos-and-donts).
					globPatterns: ['**/*.{js,css,html,svg,ico,webmanifest,woff2,json}', 'icons/*.png'],
					globIgnores: ['**/_app/immutable/assets/**/*.{avif,webp,png,jpeg,jpg,gif}']
				},
				devOptions: {
					// No SW in dev: cache-first assumes the immutable versioned shell only a
					// production build emits. The worker guards on the manifest's presence,
					// so it stays inert in dev even if a stale registration lingers.
					enabled: false
				}
			}),
			Icons({
				compiler: 'svelte'
			})
		],
		optimizeDeps: {
			// The service worker (src/service-worker.ts) is a separate SvelteKit entry
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
		// through the SvelteKit plugin above: that is what resolves `$lib`/`$app`
		// and compiles runes in `*.svelte.test.ts` files. See docs/testing.md.
		test: {
			// Also matches `*.svelte.test.ts`, where runes are available.
			include: ['src/**/*.test.ts'],
			// No DOM: component tests are deliberately out of scope (ADR-0011).
			environment: 'node'
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
