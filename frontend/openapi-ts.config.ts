import { defineConfig } from '@hey-api/openapi-ts';

// Generates the SDK, types and TanStack Query options from the committed spec
// (`just frontend-generate-api`) — see
// docs/sketches/hey-api-tanstack-query-migration.md. This replaced the
// openapi-typescript + openapi-fetch stack entirely; scripts/check-generated-api.mjs
// is the CI drift check (mirrors the old generate-api:check).
export default defineConfig({
	input: '../shared/openapi/openapi.json',
	output: {
		path: 'src/lib/api/client',
		// Prettier only, not ESLint: the generator's own patterns (`any`, index
		// signatures it can't type narrower, etc.) trip this repo's type-aware
		// lint rules in ways `eslint --fix` can't resolve, so linting here would
		// just break generation. The directory stays excluded from both
		// `pnpm lint` gates (eslint.config.js, .prettierignore) regardless —
		// this only makes the committed output pleasant to read.
		postProcess: ['prettier']
	},
	plugins: [
		'@hey-api/client-fetch',
		'@hey-api/typescript',
		'@hey-api/sdk',
		'@tanstack/svelte-query'
	]
});
