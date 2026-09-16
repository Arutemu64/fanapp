import { defineConfig } from '@hey-api/openapi-ts';

// Generates the typed API surface from the committed OpenAPI spec into
// src/lib/api/generated/ (client.gen.ts, sdk.gen.ts, types.gen.ts,
// @tanstack/svelte-query.gen.ts, index.ts).
// The spec itself is produced by the backend and guarded by a backend test;
// drift of the generated output is caught by `pnpm generate-api:check`
// (regenerate + `git diff --exit-code`). See docs/api.md.
export default defineConfig({
	input: '../shared/openapi/openapi.json',
	output: {
		path: 'src/lib/api/generated',
		postProcess: ['prettier']
	},
	plugins: [
		'@hey-api/client-fetch',
		'@hey-api/typescript',
		'@hey-api/sdk',
		// Query options / mutation options / query keys for TanStack Query, derived
		// from the same spec as the SDK — so a renamed operation breaks the query at
		// compile time instead of leaving a stale hand-written key behind.
		'@tanstack/svelte-query'
	]
});
