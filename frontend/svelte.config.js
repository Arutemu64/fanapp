import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// SPA build: the app is client-rendered, so there is no server.
		// adapter-static emits a static bundle and a `fallback` page that an
		// NGINX container serves for every unknown route, letting the client
		// router take over. See https://svelte.dev/docs/kit/single-page-apps
		adapter: adapter({
			fallback: '200.html'
		})
	}
};

export default config;
