import { defineConfig } from '@hey-api/openapi-ts';

// Generates the typed API surface from the committed OpenAPI spec into
// src/lib/api/generated/ (client.gen.ts, sdk.gen.ts, types.gen.ts,
// @tanstack/svelte-query.gen.ts, index.ts). The spec itself is produced by the
// backend and guarded by a backend test; drift of the generated output is caught
// by `pnpm generate-api:check` (regenerate + `git diff --exit-code`). See docs/api.md.
export default defineConfig({
	input: '../shared/openapi/openapi.json',
	output: {
		path: 'src/lib/api/generated',
		postProcess: ['prettier']
	},
	plugins: [
		{
			name: '@hey-api/client-fetch',
			// The generated module-level `client` is the single client the whole app
			// uses, so every TanStack Query `*Options()` helper carries our baseUrl and
			// cookie credentials without callers threading a client through.
			runtimeConfigPath: './src/lib/api/heyApiConfig'
		},
		'@hey-api/typescript',
		'@hey-api/sdk',
		{
			name: '@tanstack/svelte-query',
			queryOptions: true,
			infiniteQueryOptions: true,
			mutationOptions: true
		}
	]
});
