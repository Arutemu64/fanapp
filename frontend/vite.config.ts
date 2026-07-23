import { sentrySvelteKit } from '@sentry/sveltekit';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import Icons from 'unplugin-icons/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
	// Load .env from the repo root (`envDir: '..'`) so local `pnpm dev` reads the
	// SAME single `.env` the backend and docker-compose use — no separate
	// `frontend/.env` to drift (`.env.example` is the one source of truth; see
	// AGENTS.md). NOTE: this `envDir` governs Vite's own env (`import.meta.env`)
	// and the vite-side vars read below (port, proxy target). The frontend's
	// PUBLIC_* vars (`$env/static/public`) are loaded SEPARATELY by SvelteKit via
	// `kit.env.dir: '../'` in svelte.config.js — Vite's `envDir` does NOT govern
	// `$env/*`. Both point at the root so everything reads one file.
	//
	// `env` merges the root `.env` (loadEnv, all keys) with process.env, letting
	// process.env WIN — docker-compose injects FRONTEND_PORT / VITE_API_PROXY_TARGET
	// as container env, and an explicit shell override should also take precedence.
	// In the Docker build/dev container `..` has no `.env`, so loadEnv is empty
	// there and process.env (the build args / compose env) drives everything.
	const env = { ...loadEnv(mode, '..', ''), ...process.env };
	return {
		envDir: '..',
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
