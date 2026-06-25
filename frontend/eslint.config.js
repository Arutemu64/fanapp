import { includeIgnoreFile } from '@eslint/compat';
import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import perfectionist from 'eslint-plugin-perfectionist';
import svelte from 'eslint-plugin-svelte';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import path from 'node:path';
import ts from 'typescript-eslint';

import svelteConfig from './svelte.config.js';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	{ ignores: ['src/lib/api/v1.d.ts'] },
	js.configs.recommended,
	ts.configs.recommendedTypeChecked,
	svelte.configs.recommended,
	prettier,
	svelte.configs.prettier,
	{
		// Type-checked rules need type information; point the parser at the
		// nearest tsconfig via the project service for every linted TS file.
		languageOptions: {
			globals: { ...globals.browser, ...globals.node },
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname
			}
		},
		rules: {
			// typescript-eslint strongly recommend that you do not use the no-undef lint rule on TypeScript projects.
			// see: https://typescript-eslint.io/troubleshooting/faqs/eslint/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
			'no-undef': 'off',
			// verbatimModuleSyntax is on, so type-only imports must be elided.
			// Enforce (and autofix) a separate `import type` for them.
			'@typescript-eslint/consistent-type-imports': [
				'error',
				{ prefer: 'type-imports', fixStyle: 'separate-type-imports' }
			],
			// Let an underscore prefix mark an intentionally-unused binding.
			'@typescript-eslint/no-unused-vars': [
				'error',
				{
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_',
					caughtErrorsIgnorePattern: '^_',
					ignoreRestSiblings: true
				}
			]
		}
	},
	{
		// Import/export ordering only. We deliberately do NOT enable the full
		// `recommended-*` preset, which would also reorder object keys, union
		// members and JSX/Svelte attributes across the whole codebase.
		// `type: 'natural'` keeps numeric segments human-sorted (e.g. v2 < v10).
		plugins: { perfectionist },
		rules: {
			'perfectionist/sort-imports': ['error', { type: 'natural' }],
			'perfectionist/sort-named-imports': ['error', { type: 'natural' }],
			'perfectionist/sort-exports': ['error', { type: 'natural' }],
			'perfectionist/sort-named-exports': ['error', { type: 'natural' }]
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser,
				svelteConfig
			}
		},
		rules: {
			// ESLint can't see template-side reads of $bindable() props, so this
			// rule produces false positives for every $bindable() default in a
			// destructuring. Disable it for Svelte files where template bindings
			// satisfy the "used" requirement that ESLint can't verify.
			'no-useless-assignment': 'off'
		}
	},
	{
		// These files live outside the SvelteKit TS project: root config files,
		// build scripts, and the service worker (which SvelteKit deliberately
		// excludes from the app tsconfig). The project service can't resolve
		// them, so turn off type-aware linting here to avoid parser errors.
		files: ['eslint.config.js', 'svelte.config.js', 'scripts/**', 'src/service-worker.ts'],
		extends: [ts.configs.disableTypeChecked]
	}
);
