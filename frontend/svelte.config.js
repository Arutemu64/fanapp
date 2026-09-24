import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// The whole monorepo shares the single root `.env` (see .env.example) —
		// the frontend has no env file of its own. `$env/static/public` loads
		// from there; real environment variables (Docker build args, CI) still
		// take precedence over the file. Path is relative to the frontend dir,
		// where all commands run (justfile, Docker WORKDIR).
		env: { dir: '..' },
		// SPA build: the app is client-rendered, so there is no server.
		// adapter-static emits a static bundle and a `fallback` page that an
		// NGINX container serves for every unknown route, letting the client
		// router take over. See https://svelte.dev/docs/kit/single-page-apps
		adapter: adapter({
			fallback: '200.html'
		}),
		// We register the worker manually (src/lib/utils/serviceWorker.ts) so the
		// register() promise gets a .catch(). SvelteKit's built-in registration
		// doesn't, so a browser that refuses registration (storage-partitioned
		// embeds, private modes) surfaces an uncaught "Error: Rejected" to Sentry.
		serviceWorker: {
			register: false
		},
		experimental: {
			// Wraps each level that has a +error.svelte in a <svelte:boundary>, so a
			// component that throws while rendering shows the nearest error page
			// (inside the app shell for (app) routes) and goes through handleError
			// to Sentry, instead of leaving a half-rendered page. Needs SvelteKit
			// 2.54+ / Svelte 5.53+. https://svelte.dev/docs/kit/errors
			handleRenderingErrors: true
		}
	}
};

export default config;
