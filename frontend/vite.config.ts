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
	return {
		envDir: rootDir,
		plugins: [
			sentrySvelteKit({
				// Only upload source maps when an auth token is provided (the prod
				// Docker build passes SENTRY_AUTH_TOKEN). In CI and local dev there is
				// no token, so skip the upload work instead of doing it and then
				// silently failing to upload.
				autoUploadSourceMaps: Boolean(process.env.SENTRY_AUTH_TOKEN),
				sourceMapsUploadOptions: {
					org: 'fanfan',
					project: 'fanapp',
					url: 'https://glitchtip.sixty-four.ru/'
				}
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
