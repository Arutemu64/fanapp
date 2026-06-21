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
		allowedHosts: true
	}
});
