import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		env: {
			// Load .env from the repo root so `$env/static/public` (PUBLIC_* vars)
			// comes from the SAME single `.env` the backend and docker-compose use
			// — no separate `frontend/.env` to drift (`.env.example` is the one
			// source of truth; see AGENTS.md). Vite's own `envDir` does NOT govern
			// `$env/*`; SvelteKit loads it from here, so this is the setting that
			// matters for the frontend's public env. Docker image builds are
			// unaffected: they inject PUBLIC_* as build args (process.env), which
			// win, and the root `.env` isn't in the `./frontend` build context.
			//
			// Footgun: this makes the whole root `.env` (incl. backend secrets like
			// DB__PASSWORD) reachable via `$env/*/private`. This is a serverless
			// static SPA (adapter-static) — never import `$env/static/private` or
			// `$env/dynamic/private` here, or a secret could be baked into a
			// prerendered asset. Only `PUBLIC_*` vars may be used.
			dir: '../'
		},
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
