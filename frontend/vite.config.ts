import { sentrySvelteKit } from '@sentry/sveltekit';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';
import Icons from 'unplugin-icons/vite';
import { defineConfig, loadEnv } from 'vite';

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
				autoUploadSourceMaps: canUploadSourceMaps
			}),
			tailwindcss(),
			sveltekit(),
			Icons({
				compiler: 'svelte'
			})
		],
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
