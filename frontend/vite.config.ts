import { sentrySvelteKit } from '@sentry/sveltekit';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import Icons from 'unplugin-icons/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sentrySvelteKit({
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
