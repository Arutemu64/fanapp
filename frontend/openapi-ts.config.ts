import { defineConfig } from '@hey-api/openapi-ts';

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
		'@tanstack/svelte-query'
	]
});
