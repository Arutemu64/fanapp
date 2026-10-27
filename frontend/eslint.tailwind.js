import betterTailwindcss from 'eslint-plugin-better-tailwindcss';

const VARIANTS = '^(?:.*:)?';
const MODIFIER = '(?:/[^:]+)?$';
const PALETTE_HUES =
	'red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone';
const COLOR_UTILITIES =
	'text|bg|border(?:-[trblxyse])?|ring|ring-offset|fill|stroke|from|via|to|outline|decoration|divide|placeholder|caret|accent|shadow';

export const RESTRICTION_GROUPS = {
	type: [
		{
			pattern: `${VARIANTS}(?:sm|md|lg|xl|2xl|@[a-z0-9]+|min-\\[[^\\]]+\\]|max-[a-z0-9-]+):(?:.*:)?text-(?:[23]?xs|sm|base|lg|[2-9]?xl|headline|section|body)${MODIFIER}`,
			message:
				'Type sizes do not change with screen width (DESIGN.md Fixed-Scale Rule): drop the breakpoint and use one size, text-headline / text-section / text-body, or text-sm / text-xs for secondary text.'
		},
		{
			pattern: `${VARIANTS}text-(?:lg|[2-9]?xl)${MODIFIER}`,
			message:
				'Use a type role from app.css @theme instead of a raw heading size: text-headline (page and card titles, 24px) or text-section (section headings, 18px). See docs/frontend.md "Typography Scale".'
		},
		{
			pattern: `${VARIANTS}text-\\[(?:\\d|calc|length:|var\\().*\\]${MODIFIER}`,
			message:
				'No arbitrary font sizes. Use a type role (text-headline / text-section / text-body) or text-sm / text-xs; a genuinely new role goes in app.css @theme and cn() in $lib/utils.ts.'
		}
	],
	palette: [
		{
			pattern: `${VARIANTS}(?:${COLOR_UTILITIES})-(?:${PALETTE_HUES})-\\d{2,3}${MODIFIER}`,
			message:
				'Use a semantic colour token, not a raw palette hue: text-foreground / text-muted-foreground, bg-muted, border-border, text-destructive, text-success / text-warning / text-info, or the brand primary / secondary. See DESIGN.md §2.'
		},
		{
			pattern: `${VARIANTS}(?:${COLOR_UTILITIES})-\\[(?:#|rgb|hsl|oklch|color:).*\\]${MODIFIER}`,
			message:
				'No arbitrary colours. Use a semantic token from app.css, or add one there (light and dark values) if the meaning is new.'
		}
	],
	zIndex: [
		{
			pattern: `${VARIANTS}-?z-(?:3[1-9]|[4-9]\\d|\\d{3,}|\\[.*\\])$`,
			message:
				'Above the in-page sticky band (z-10 to z-30), use the ladder tokens: z-(--z-chrome) or z-(--z-overlay). See docs/frontend.md "Z-Index Scale".'
		}
	]
};

/** @param {...keyof typeof RESTRICTION_GROUPS} exempt */
function restrictedClasses(...exempt) {
	return Object.entries(RESTRICTION_GROUPS)
		.filter(([group]) => !exempt.includes(/** @type {keyof typeof RESTRICTION_GROUPS} */ (group)))
		.flatMap(([, restrictions]) => restrictions);
}

const restrictedClassExemptions = [
	{
		files: [
			'src/routes/(app)/components/home/HeroCard.svelte',
			'src/routes/(app)/components/AppBottomNav.svelte',
			'src/routes/(app)/(protected)/tools/components/OnlineNowCard.svelte',
			'src/lib/components/VerificationCodeInput.svelte'
		],
		rules: {
			'better-tailwindcss/no-restricted-classes': [
				'error',
				{ restrict: restrictedClasses('type', 'palette') }
			]
		}
	},
	{
		files: ['src/lib/data/socialProviders.ts', 'src/routes/(app)/profile/+page.svelte'],
		rules: {
			'better-tailwindcss/no-restricted-classes': [
				'error',
				{ restrict: restrictedClasses('palette') }
			]
		}
	}
];

export const tailwindConfigs = [
	{
		files: ['src/**/*.{svelte,ts,js}'],
		extends: [betterTailwindcss.configs['recommended-error']],
		settings: { 'better-tailwindcss': { entryPoint: 'src/app.css' } },
		rules: {
			'better-tailwindcss/enforce-consistent-class-order': 'off',
			'better-tailwindcss/enforce-consistent-line-wrapping': 'off',
			'better-tailwindcss/enforce-canonical-classes': [
				'error',
				{ ignore: ['^(?:.*:)?text-(?:headline|section|body)$', '^(?:.*:)?leading-'] }
			],
			'better-tailwindcss/no-unknown-classes': [
				'error',
				{ ignore: ['^toaster$', '^countdown-cell(--animated)?$', '^tick$'] }
			],
			'better-tailwindcss/no-restricted-classes': ['error', { restrict: restrictedClasses() }],
			'better-tailwindcss/no-conflicting-classes': 'error'
		}
	},
	...restrictedClassExemptions,
	{
		files: ['src/lib/components/ui/**'],
		rules: {
			'better-tailwindcss/enforce-canonical-classes': 'off',
			'better-tailwindcss/no-deprecated-classes': 'off',
			'better-tailwindcss/no-duplicate-classes': 'off',
			'better-tailwindcss/no-restricted-classes': 'off'
		}
	},
	{
		files: ['src/**/*.test.ts'],
		rules: { 'better-tailwindcss/no-concatenated-classes': 'off' }
	}
];
