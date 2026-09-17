import { defineConfig } from '@hey-api/openapi-ts';

// Generates the typed API surface from the committed OpenAPI spec into
// src/lib/api/generated/ (client.gen.ts, sdk.gen.ts, types.gen.ts, index.ts).
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
		{
			name: '@hey-api/client-fetch',
			// Base URL and cookie policy are applied at client creation, so the
			// generated TanStack helpers (which capture the singleton at import time)
			// never see an unconfigured client. See src/lib/api/heyApiConfig.ts.
			runtimeConfigPath: './src/lib/api/heyApiConfig'
		},
		'@hey-api/typescript',
		'@hey-api/sdk',
		{
			// Emits `<operation>Options()` / `<operation>Mutation()` helpers that feed
			// straight into TanStack Query, so query keys and fetchers are derived from
			// the spec instead of hand-written per call site.
			name: '@tanstack/svelte-query',
			// The paginated feeds (notifications, schedule changes, feedback,
			// broadcasts, users) are limit/offset endpoints rendered as "load more",
			// which is what `createInfiniteQuery` is for.
			infiniteQueryOptions: true
		}
	]
});
