import comments from '@eslint-community/eslint-plugin-eslint-comments/configs';
import js from '@eslint/js';
import { loadConfig } from '@sveltejs/load-config';
import vitest from '@vitest/eslint-plugin';
import prettier from 'eslint-config-prettier';
import perfectionist from 'eslint-plugin-perfectionist';
import playwright from 'eslint-plugin-playwright';
import svelte from 'eslint-plugin-svelte';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import globals from 'globals';
import path from 'node:path';
import ts from 'typescript-eslint';

import { tailwindConfigs } from './eslint.tailwind.js';

const {
	typescript: _typescript,
	version: _version,
	...svelteConfig
} = (await loadConfig('./', { traverse: false }))?.config ?? {};

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	{ ignores: ['src/lib/api/generated/', 'src/lib/paraglide/'] },
	js.configs.recommended,
	ts.configs.strictTypeChecked,
	ts.configs.stylisticTypeChecked,
	svelte.configs.recommended,
	prettier,
	svelte.configs.prettier,
	comments.recommended,
	{
		linterOptions: {
			reportUnusedDisableDirectives: 'error',
			reportUnusedInlineConfigs: 'error'
		}
	},
	{
		languageOptions: {
			globals: { ...globals.browser, ...globals.node },
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname,
				extraFileExtensions: ['.svelte']
			}
		},
		rules: {
			'no-undef': 'off',
			'@typescript-eslint/consistent-type-imports': [
				'error',
				{ prefer: 'type-imports', fixStyle: 'separate-type-imports' }
			],
			'@typescript-eslint/no-unused-vars': [
				'error',
				{
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_',
					caughtErrorsIgnorePattern: '^_',
					ignoreRestSiblings: true
				}
			],
			'@eslint-community/eslint-comments/require-description': [
				'error',
				{ ignore: ['eslint-enable'] }
			],
			'@eslint-community/eslint-comments/no-restricted-disable': [
				'error',
				'better-tailwindcss/no-restricted-classes',
				'better-tailwindcss/no-unknown-classes'
			],
			'@typescript-eslint/strict-boolean-expressions': [
				'error',
				{ allowNullableString: true, allowNullableBoolean: true }
			],
			'@typescript-eslint/no-confusing-void-expression': ['error', { ignoreArrowShorthand: true }],
			'@typescript-eslint/switch-exhaustiveness-check': [
				'error',
				{ considerDefaultExhaustiveForUnions: true, requireDefaultForNonUnion: true }
			],
			'@typescript-eslint/require-array-sort-compare': ['error', { ignoreStringArrays: true }],
			'@typescript-eslint/prefer-readonly': 'error',
			eqeqeq: ['error', 'smart'],
			'@typescript-eslint/restrict-template-expressions': ['error', { allowNumber: true }],
			'no-implicit-coercion': ['error', { allow: ['!!'] }],
			'no-param-reassign': 'error',
			complexity: ['error', 10],
			'max-depth': ['error', 3],
			'max-params': ['error', 4],
			'max-lines-per-function': ['error', { max: 60, skipBlankLines: true, skipComments: true }],
			'no-nested-ternary': 'error',
			'no-negated-condition': 'error',
			'no-else-return': ['error', { allowElseIf: false }],
			'no-lonely-if': 'error',
			'no-unneeded-ternary': ['error', { defaultAssignment: false }],
			'no-useless-return': 'error',
			'no-useless-rename': 'error',
			'no-useless-computed-key': 'error',
			'no-useless-concat': 'error',
			'object-shorthand': 'error',
			'arrow-body-style': 'error',
			'prefer-arrow-callback': 'error',
			'prefer-template': 'error',
			'prefer-object-has-own': 'error',
			'logical-assignment-operators': 'error',
			'default-case-last': 'error',
			'@typescript-eslint/no-shadow': 'error',
			// Property signatures are checked contravariantly under strictFunctionTypes; methods are not.
			'@typescript-eslint/method-signature-style': 'error',
			'@typescript-eslint/consistent-type-exports': 'error',
			'@typescript-eslint/no-import-type-side-effects': 'error',
			'@typescript-eslint/no-useless-empty-export': 'error',
			'@typescript-eslint/non-nullable-type-assertion-style': 'off',
			'@typescript-eslint/no-empty-function': ['error', { allow: ['arrowFunctions'] }],
			'@typescript-eslint/prefer-nullish-coalescing': [
				'error',
				{ ignorePrimitives: { string: true, boolean: true } }
			],
			'no-console': ['error', { allow: ['warn', 'error'] }],
			'no-restricted-imports': [
				'error',
				{
					paths: [
						{
							name: '@lucide/svelte',
							message: "Import each icon from '@lucide/svelte/icons/<name>' instead."
						}
					]
				}
			]
		}
	},
	{
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
				parser: ts.parser,
				svelteConfig
			}
		},
		rules: {
			'no-useless-assignment': 'off',
			'@typescript-eslint/no-useless-default-assignment': 'off',
			'@typescript-eslint/no-confusing-void-expression': 'off',
			'svelte/block-lang': ['error', { script: 'ts', style: [null, 'css'] }],
			'svelte/button-has-type': 'error',
			'svelte/no-bind-value-on-checkable-inputs': 'error',
			'svelte/no-conflicting-module-names': 'error',
			'svelte/no-ignored-unsubscribe': 'error',
			'svelte/no-nested-style-tag': 'error',
			'svelte/no-target-blank': ['error', { allowReferrer: true }],
			'svelte/no-top-level-browser-globals': 'error',
			'svelte/prefer-derived-over-derived-by': 'error',
			'svelte/require-store-callbacks-use-set-param': 'error',
			'svelte/valid-style-parse': 'error',
			'svelte/no-at-const-tags': 'error',
			'prefer-const': 'off',
			'svelte/prefer-const': 'error',
			'svelte/shorthand-attribute': 'error',
			'svelte/shorthand-directive': 'error'
		}
	},
	{
		files: ['**/*.svelte'],
		rules: { 'svelte/no-add-event-listener': 'error' }
	},
	{
		files: ['e2e/**/*.ts'],
		extends: [playwright.configs['flat/recommended']],
		// page.evaluate callbacks run in the browser and take their outer values as same-named args.
		rules: { '@typescript-eslint/no-shadow': 'off' }
	},
	{
		files: ['e2e/gallery/**/*.ts'],
		rules: {
			'playwright/expect-expect': 'off',
			'playwright/no-networkidle': 'off'
		}
	},
	{
		files: ['src/**/*.test.ts'],
		extends: [vitest.configs.recommended]
	},
	{
		files: ['src/**/*.test.ts', 'e2e/**/*.ts'],
		rules: {
			'max-lines-per-function': 'off',
			'max-params': 'off',
			'@typescript-eslint/no-empty-function': 'off'
		}
	},
	...tailwindConfigs,
	{
		files: ['src/lib/components/ui/button/button.svelte'],
		rules: {
			'svelte/no-navigation-without-resolve': 'off'
		}
	},
	{
		files: ['src/lib/components/ui/**'],
		rules: {
			'@typescript-eslint/no-unnecessary-condition': 'off',
			'@typescript-eslint/strict-boolean-expressions': 'off',
			'svelte/no-add-event-listener': 'off',
			'@typescript-eslint/no-unsafe-argument': 'off',
			'@typescript-eslint/no-unsafe-assignment': 'off',
			'@typescript-eslint/no-unsafe-call': 'off',
			'@typescript-eslint/no-unsafe-member-access': 'off',
			'@typescript-eslint/no-unsafe-return': 'off',
			complexity: 'off',
			'max-depth': 'off',
			'max-params': 'off',
			'max-lines-per-function': 'off',
			'no-nested-ternary': 'off',
			'no-negated-condition': 'off',
			'@typescript-eslint/no-shadow': 'off',
			'@typescript-eslint/array-type': 'off',
			'@typescript-eslint/consistent-type-definitions': 'off',
			'@typescript-eslint/no-empty-function': 'off',
			'@typescript-eslint/prefer-nullish-coalescing': 'off',
			'@typescript-eslint/prefer-optional-chain': 'off'
		}
	},
	{
		files: [
			'eslint.config.js',
			'eslint.tailwind.config.js',
			'eslint.tailwind.js',
			'openapi-ts.config.ts',
			'playwright.config.ts',
			'playwright.gallery.config.ts'
		],
		extends: [ts.configs.disableTypeChecked]
	},
	{
		files: ['vite.config.ts'],
		rules: { 'max-lines-per-function': 'off' }
	}
);
