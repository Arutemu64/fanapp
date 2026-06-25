import { sentrySvelteKit } from '@sentry/sveltekit';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import Icons from 'unplugin-icons/vite';
import { defineConfig } from 'vite';

export default defineConfig({
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
		// In dev the frontend and backend run on different origins, but the app
		// calls the API with a relative base (`PUBLIC_API_URL=/api`). Proxy `/api`
		// to the backend so dev mirrors the same-origin prod setup (Caddy) and
		// needs no CORS. http-proxy streams responses, so SSE (`/api/events`) works.
		proxy: {
			'/api': {
				// Mirror Caddy's `handle_path /api*` — strip the prefix; the backend
				// serves routes at root (uvicorn root_path="/api" is informational).
				target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	}
});
