// Tailwind-only lint config for the PostToolUse edit hook (.claude/hooks/post-edit-check.py).
// No type information and no other rule sets, so linting one file takes ~1s instead of the
// main config's ~9s; CI and pre-commit still run the full eslint.config.js.
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
		// ~2.5s of Tailwind startup, and only ever autofixable spelling; pre-commit fixes
		// it. The hook is for the design restrictions an agent has to act on.
		files: ['**/*'],
		rules: { 'better-tailwindcss/enforce-canonical-classes': 'off' }
	}
);
