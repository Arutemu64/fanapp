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
			'svelte/no-at-const-tags': 'error'
		}
	},
	{
		files: ['**/*.svelte'],
		rules: { 'svelte/no-add-event-listener': 'error' }
	},
	{
		files: ['e2e/**/*.ts'],
		extends: [playwright.configs['flat/recommended']]
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
			'@typescript-eslint/no-unsafe-return': 'off'
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
	}
);
