import { defineConfig } from '@hey-api/openapi-ts';

// Generates the typed API surface from the committed OpenAPI spec into
// src/lib/api/generated/ (client.gen.ts, sdk.gen.ts, types.gen.ts, index.ts),
// plus the TanStack Query options/keys for every operation
// (@tanstack/vue-query.gen.ts, https://heyapi.dev/openapi-ts/plugins/tanstack-query).
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
		{ name: '@hey-api/client-fetch', runtimeConfigPath: '#lib/api/clientConfig.js' },
		'@hey-api/typescript',
		'@hey-api/sdk',
		'@tanstack/vue-query'
	]
});
