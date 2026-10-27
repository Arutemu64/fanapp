import svelte from 'eslint-plugin-svelte';
import { defineConfig } from 'eslint/config';
import ts from 'typescript-eslint';

import { tailwindConfigs } from './eslint.tailwind.js';

export default defineConfig(
	{ ignores: ['src/lib/api/generated/', 'src/lib/paraglide/'] },
	{ files: ['**/*.ts', '**/*.js'], languageOptions: { parser: ts.parser } },
	svelte.configs.base,
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: { parserOptions: { parser: ts.parser } }
	},
	...tailwindConfigs,
	{
		files: ['**/*'],
		rules: { 'better-tailwindcss/enforce-canonical-classes': 'off' }
	}
);
