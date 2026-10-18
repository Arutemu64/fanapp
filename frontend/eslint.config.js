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

// SvelteKit 3 keeps the Svelte config in vite.config.ts; load-config reads it from
// there (https://sveltejs.github.io/eslint-plugin-svelte/user-guide/). Two resolved
// keys are dropped; neither the parser nor the plugin reads them:
// - `typescript` holds a function default, which `eslint --cache` cannot serialize.
// - `version.name` defaults to Date.now() (https://svelte.dev/docs/kit/configuration#version),
//   so it changes the config hash on every run and `--cache` re-lints every Svelte file.
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
		// A stale or blanket suppression is how a rule quietly stops applying, so
		// both are errors, not ESLint's default warning that CI lets through.
		linterOptions: {
			reportUnusedDisableDirectives: 'error',
			reportUnusedInlineConfigs: 'error'
		}
	},
	{
		// Type-checked rules need type information; point the parser at the
		// nearest tsconfig via the project service for every linted TS file.
		languageOptions: {
			globals: { ...globals.browser, ...globals.node },
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname,
				// Declare `.svelte` here, globally, not only in the Svelte override.
				// With projectService, differing extraFileExtensions across files in
				// the same TS project forces a full project reload per file, turning
				// a cold lint of this repo from ~2min into ~15s once made consistent.
				// https://typescript-eslint.io/troubleshooting/typed-linting/performance/
				extraFileExtensions: ['.svelte']
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
			],
			// Guardrails beyond strictTypeChecked, aimed at the shortcuts generated code
			// takes: a suppression must say why (`-- reason`), and the Tailwind design
			// rules carry their exemptions in eslint.tailwind.js, never inline.
			'@eslint-community/eslint-comments/require-description': [
				'error',
				{ ignore: ['eslint-enable'] }
			],
			'@eslint-community/eslint-comments/no-restricted-disable': [
				'error',
				'better-tailwindcss/no-restricted-classes',
				'better-tailwindcss/no-unknown-classes'
			],
			// Nullable strings and booleans read naturally as "absent" in a condition;
			// what stays banned is `any`, an always-truthy object, and a nullable number,
			// whose `0` is the classic falsy slip.
			'@typescript-eslint/strict-boolean-expressions': [
				'error',
				{ allowNullableString: true, allowNullableBoolean: true }
			],
			// `() => clearTimeout(id)` is clear as written; bracing every shorthand
			// arrow adds noise without catching anything.
			'@typescript-eslint/no-confusing-void-expression': ['error', { ignoreArrowShorthand: true }],
			'@typescript-eslint/switch-exhaustiveness-check': [
				'error',
				{ considerDefaultExhaustiveForUnions: true, requireDefaultForNonUnion: true }
			],
			'@typescript-eslint/require-array-sort-compare': ['error', { ignoreStringArrays: true }],
			'@typescript-eslint/prefer-readonly': 'error',
			eqeqeq: ['error', 'smart'],
			'@typescript-eslint/restrict-template-expressions': ['error', { allowNumber: true }],
			// `!!x` is the idiomatic boolean cast; the rule is here for `+x` and `'' + x`.
			'no-implicit-coercion': ['error', { allow: ['!!'] }],
			'no-param-reassign': 'error',
			'no-console': ['error', { allow: ['warn', 'error'] }],
			// The barrel re-exports every Lucide icon, and Vitest transforms all of them
			// for any test that reaches it: one test importing src/lib/data/tools.ts
			// took 26s of a 27s cold run. https://vite.dev/guide/performance#avoid-barrel-files
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
				parser: ts.parser,
				svelteConfig
			}
		},
		rules: {
			// Known false positive with $bindable props: ESLint sees the write-out to the
			// parent but not the parent-side bind read, and flags it incorrectly.
			// Tracked: sveltejs/eslint-plugin-svelte#1478 — re-enable once fixed.
			'no-useless-assignment': 'off',
			// The rule reads `open = $bindable(false)` as a default the prop's type
			// makes unreachable, and its autofix deletes the `$bindable()` with it,
			// which silently turns a two-way binding into a one-way prop.
			'@typescript-eslint/no-useless-default-assignment': 'off',
			// Every `{@render snippet()}` tag reads as a void call used as a value.
			'@typescript-eslint/no-confusing-void-expression': 'off',
			// Opt-in correctness rules outside svelte.configs.recommended. Top-level
			// browser globals crash the server render; the rest catch Svelte-specific
			// slips that type-checking doesn't see.
			'svelte/block-lang': ['error', { script: 'ts', style: [null, 'css'] }],
			'svelte/button-has-type': 'error',
			'svelte/no-bind-value-on-checkable-inputs': 'error',
			'svelte/no-conflicting-module-names': 'error',
			'svelte/no-ignored-unsubscribe': 'error',
			'svelte/no-nested-style-tag': 'error',
			// noopener is the security half; the Referer is ours to send.
			'svelte/no-target-blank': ['error', { allowReferrer: true }],
			'svelte/no-top-level-browser-globals': 'error',
			'svelte/prefer-derived-over-derived-by': 'error',
			'svelte/require-store-callbacks-use-set-param': 'error',
			'svelte/valid-style-parse': 'error',
			// `{@const}` is legacy since Svelte 5.56; the fix writes `{const x = $derived(y)}`.
			'svelte/no-at-const-tags': 'error'
		}
	},
	{
		// In a component, `on()` from svelte/events keeps handler order consistent
		// with Svelte's delegated events, which a raw addEventListener bypasses.
		// .svelte.ts services stay free to use it: their EventSource and window
		// listeners never meet a delegated handler.
		files: ['**/*.svelte'],
		rules: { 'svelte/no-add-event-listener': 'error' }
	},
	{
		files: ['e2e/**/*.ts'],
		extends: [playwright.configs['flat/recommended']]
	},
	{
		// The README gallery runs through the Playwright runner but captures screenshots
		// rather than asserting, and waits for every mocked image request to finish.
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
		// Design-system primitive renders <a href={...}> from an external/variable href.
		files: ['src/lib/components/ui/button/button.svelte'],
		rules: {
			'svelte/no-navigation-without-resolve': 'off'
		}
	},
	{
		// Vendored shadcn-svelte primitives. Some wrap another local primitive via
		// `ComponentProps<typeof Input>` etc.; typescript-eslint's type service does
		// not run svelte2tsx, so a type originating in a `.svelte` file resolves to
		// `any` and trips the no-unsafe family — a false positive (svelte-check/tsc
		// type these correctly). Relax only that family here, and only for the
		// generated `ui/` sources, so `shadcn-svelte` components stay unedited and
		// `shadcn-svelte update`-able. See sveltejs/svelte#16264.
		files: ['src/lib/components/ui/**'],
		rules: {
			// strictTypeChecked's condition checks flag that `any` and upstream's
			// defensive optional chains alike; both stay as upstream ships them.
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
			'eslint.tailwind.config.js',
			'eslint.tailwind.js',
			'openapi-ts.config.ts',
			'playwright.config.ts',
			'playwright.gallery.config.ts'
		],
		extends: [ts.configs.disableTypeChecked]
	}
);
