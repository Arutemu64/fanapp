import { sentrySvelteKit } from '@sentry/sveltekit';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
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
		// Dev runs Vite (not the prod NGINX), so proxy /api to the backend here to
		// keep the same single-origin contract as production. Target is the local
		// backend by default; the dev container overrides it to the api service.
		proxy: {
			'/api': {
				target: process.env.BACKEND_ORIGIN ?? 'http://localhost:8000',
				changeOrigin: true,
				// Strip the /api prefix; the backend is mounted at root with
				// UVICORN_ROOT_PATH=/api handling public URL generation.
				rewrite: (path) => path.replace(/^\/api/, ''),
				// Keep SSE (/api/events) streaming instead of buffered.
				ws: true
			}
		}
	}
});
