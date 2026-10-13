import { sentryVitePlugin } from '@sentry/vite-plugin';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';
import Icons from 'unplugin-icons/vite';
import { loadEnv, type Plugin } from 'vite';
import { imagetools } from 'vite-imagetools';
import { VitePWA } from 'vite-plugin-pwa';
import { defineConfig } from 'vitest/config';

// The whole monorepo shares the single root `.env` (see .env.example); the
// frontend has no env file of its own. `envDir` points Vite's own env loading
// (import.meta.env) at the repo root, and `loadEnv` below does the same for
// this config file itself — Vite deliberately does not inject .env files into
// process.env while the config is being evaluated, so `process.env.X` alone
// would miss values set in the file.
const rootDir = fileURLToPath(new URL('..', import.meta.url));

// Every public variable src/lib/env.ts reads. The bundle is static, so a missing one
// would only surface as `undefined` at runtime; failing the build keeps the
// "must exist, even if empty" contract the SvelteKit env module used to enforce.
const PUBLIC_ENV_KEYS = [
	'PUBLIC_SENTRY_DSN',
	'PUBLIC_SENTRY_ENVIRONMENT',
	'PUBLIC_SENTRY_TRACES_SAMPLE_RATE',
	'PUBLIC_API_URL',
	'PUBLIC_VAPID_KEY',
	'PUBLIC_VK_GROUP_ID',
	'PUBLIC_TIMEZONE',
	'PUBLIC_SMARTCAPTCHA_CLIENT_KEY',
	// Only read by the %PUBLIC_SITE_URL% placeholders in index.html.
	'PUBLIC_SITE_URL'
] as const;

function requirePublicEnv(env: Record<string, string>): Plugin {
	return {
		name: 'fanfan:require-public-env',
		buildStart() {
			const missing = PUBLIC_ENV_KEYS.filter((key) => env[key] === undefined);
			if (missing.length > 0) {
				this.error(
					`Missing public env var(s): ${missing.join(', ')}. Declare them (an empty value is fine) in the root .env or the build environment.`
				);
			}
		}
	};
}

export default defineConfig(({ mode, command }) => {
	// Empty prefix = load every variable, not just PUBLIC_*. Only this config
	// reads the result; client exposure stays gated by `envPrefix` below. Real
	// environment variables (Docker, CI) win over file values — loadEnv applies
	// process.env last, matching Vite's documented precedence.
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
		url: env.SENTRY_URL,
		authToken: env.SENTRY_AUTH_TOKEN
	};
	// With any part missing (CI, local dev) skip the upload work instead of
	// doing it and then failing to upload.
	const canUploadSourceMaps = Object.values(sentryUpload).every(Boolean);

	// The commit SHA when the build has one, else a timestamp: either way a value
	// that differs between builds, which is all the cache buster and the precache
	// revision need.
	const buildId = env.APP_BUILD || Date.now().toString(36);

	return {
		envDir: rootDir,
		// Only PUBLIC_* reaches client code. Do not widen this to SENTRY_*: that
		// prefix also covers SENTRY_AUTH_TOKEN, which must never be reachable from
		// the bundle. Also what `%PUBLIC_SITE_URL%` in index.html substitutes.
		envPrefix: 'PUBLIC_',
		// The build's identity, inlined as constants (declared in src/env.d.ts).
		// APP_VERSION/APP_BUILD are build inputs, not settings: the publish workflow
		// and `just run-prod` pass them as Docker build args, and nothing can change
		// them after the build. See docs/dependencies.md "Versioning the app".
		define: {
			__APP_VERSION__: JSON.stringify(env.APP_VERSION ?? ''),
			__APP_BUILD__: JSON.stringify(env.APP_BUILD ?? ''),
			__BUILD_ID__: JSON.stringify(buildId)
		},
		build: {
			// `build/` is where the Dockerfile and docs expect the static bundle.
			outDir: 'build',
			// Hidden maps: generated for the upload, not referenced from the bundle.
			sourcemap: canUploadSourceMaps ? 'hidden' : false
		},
		plugins: [
			requirePublicEnv(env),
			vue(),
			tailwindcss(),
			// Resized AVIF/WebP variants of the venue maps and the home hero, imported
			// with `?w=…&format=…&as=picture`.
			imagetools(),
			Icons({ compiler: 'vue3' }),
			// The worker body and its push/update/image-cache logic are hand-written
			// (src/service-worker/); the plugin only compiles it and injects the
			// precache list into `self.__WB_MANIFEST`. See ADR-0023.
			VitePWA({
				strategies: 'injectManifest',
				srcDir: 'src/service-worker',
				filename: 'service-worker.ts',
				// Registered by src/lib/utils/serviceWorker.ts, so register() gets a .catch().
				injectRegister: false,
				// public/manifest.json is hand-written and linked from index.html.
				manifest: false,
				// The worker is inert in `vite dev` (see src/service-worker/service-worker.ts).
				devOptions: { enabled: false },
				injectManifest: {
					// Emit an ES module worker; the registration passes `type: 'module'`.
					rollupFormat: 'es',
					globPatterns: [
						'assets/**/*.{js,css}',
						'assets/**/*.woff2',
						'icons/*.png',
						'*.{svg,ico,html,json}'
					],
					// Raster images stay out of the precache: the responsive variants are
					// cached at runtime instead, and og-image.png is crawler-only.
					// Font subsets a Russian UI never renders still load on demand via
					// unicode-range; latin-ext stays for romaji macrons (ō, ū).
					globIgnores: [
						'og-image.png',
						'**/*-greek-*.woff2',
						'**/*-greek-ext-*.woff2',
						'**/*-vietnamese-*.woff2'
					]
				}
			}),
			// Source-map upload only for a production build that has all the settings.
			sentryVitePlugin({
				...sentryUpload,
				disable: command !== 'build' || !canUploadSourceMaps,
				telemetry: false,
				// Names the release the maps are uploaded under and injects the same name
				// into the bundle so the SDK reports it — see the note in src/main.ts. The
				// commit SHA, matching the backend's Sentry release. Left undefined (not '')
				// when unset so the plugin's own detection, the git HEAD SHA, still applies.
				release: { name: env.APP_BUILD || undefined },
				sourcemaps: { filesToDeleteAfterUpload: ['build/**/*.map'] }
			})
		],
		// Tests live here rather than in a vitest.config.ts of their own so they share
		// the plugin chain above. See docs/testing.md.
		test: {
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
