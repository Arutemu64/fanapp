import { includeIgnoreFile } from '@eslint/compat';
import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import perfectionist from 'eslint-plugin-perfectionist';
import vue from 'eslint-plugin-vue';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import path from 'node:path';
import ts from 'typescript-eslint';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	{ ignores: ['src/lib/api/generated/'] },
	js.configs.recommended,
	ts.configs.recommendedTypeChecked,
	vue.configs['flat/recommended'],
	prettier,
	{
		// Type-checked rules need type information; point the parser at the
		// nearest tsconfig via the project service for every linted TS file.
		languageOptions: {
			globals: { ...globals.browser, ...globals.node },
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname,
				// Declare `.vue` here, globally, not only in the Vue override.
				// With projectService, differing extraFileExtensions across files in
				// the same TS project forces a full project reload per file, turning
				// a cold lint of this repo from ~2min into ~15s once made consistent.
				// https://typescript-eslint.io/troubleshooting/typed-linting/performance/
				extraFileExtensions: ['.vue']
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
		// members and JSX/Vue attributes across the whole codebase.
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
		files: ['**/*.vue'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.vue'],
				parser: ts.parser
			}
		},
		rules: {
			// The Vue tooling (vue-tsc) type-checks templates; the SFC layout is
			// fixed to script → template → style so every component reads the same way.
			'vue/block-order': ['error', { order: ['script', 'template', 'style'] }],
			'vue/component-api-style': ['error', ['script-setup']],
			'vue/define-macros-order': ['error', { order: ['defineProps', 'defineEmits'] }],
			// Prettier owns the attribute layout and self-closing style.
			'vue/html-self-closing': 'off',
			'vue/singleline-html-element-content-newline': 'off',
			'vue/multiline-html-element-content-newline': 'off'
		}
	},
	{
		// Vendored shadcn-vue primitives. Some wrap another local primitive, and
		// typescript-eslint's type service does not run vue-tsc, so a type originating
		// in a `.vue` file resolves to `any` and trips the no-unsafe family — a false
		// positive (vue-tsc types these correctly). Relax only that family here, and
		// only for the generated `ui/` sources, so the components stay unedited and
		// `shadcn-vue`-updatable. shadcn-vue's own names are single words (`Button`).
		files: ['src/lib/components/ui/**'],
		rules: {
			'vue/multi-word-component-names': 'off',
			'@typescript-eslint/no-unsafe-argument': 'off',
			'@typescript-eslint/no-unsafe-assignment': 'off',
			'@typescript-eslint/no-unsafe-call': 'off',
			'@typescript-eslint/no-unsafe-member-access': 'off',
			'@typescript-eslint/no-unsafe-return': 'off'
		}
	},
	{
		// These root config files live outside every TS project (the app's and the
		// service worker's, src/service-worker/tsconfig.json). The project service
		// can't resolve them, so turn off type-aware linting here to avoid parser
		// errors. The Playwright suite is NOT listed: e2e/tsconfig.json is the
		// nearest tsconfig for its files, so it keeps type-aware rules — notably no-floating-promises,
		// which catches a missing `await` on a Playwright call
		// (https://playwright.dev/docs/best-practices). The Playwright configs stay
		// here because their nearest tsconfig is the app one, which excludes them.
		files: [
			'eslint.config.js',
			'openapi-ts.config.ts',
			'playwright.config.ts',
			'playwright.gallery.config.ts'
		],
		extends: [ts.configs.disableTypeChecked]
	}
);
