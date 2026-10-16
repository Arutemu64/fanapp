// Tailwind class rules (eslint-plugin-better-tailwindcss; ADR-0030), shared by the main
// config and eslint.tailwind.config.js, the type-info-free config the PostToolUse edit
// hook runs on a single file. One definition, so the hook and CI cannot disagree.
import betterTailwindcss from 'eslint-plugin-better-tailwindcss';

// Design-system guardrails for Tailwind classes, grouped so a file can be exempted from
// one group with a stated reason (see restrictedClassExemptions). The `(.*:)?` prefix
// matches any variant stack (dark:, hover:, [&_h2]:...) and MODIFIER a trailing line
// height or opacity (text-sm/6, text-red-500/50). Messages name the fix, because
// the reader is often an agent that will act on exactly what the message says.
const VARIANTS = '^(?:.*:)?';
const MODIFIER = '(?:/[^:]+)?$';
const PALETTE_HUES =
	'red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone';
const COLOR_UTILITIES =
	'text|bg|border(?:-[trblxyse])?|ring|ring-offset|fill|stroke|from|via|to|outline|decoration|divide|placeholder|caret|accent|shadow';

export const RESTRICTION_GROUPS = {
	// DESIGN.md §3 and docs/frontend.md "Typography Scale".
	type: [
		{
			// The breakpoint may sit anywhere in the stack: sm:hover:text-base.
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
	// DESIGN.md "Color-Earns-Its-Place" and the semantic tokens in app.css.
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
	// docs/frontend.md "Z-Index Scale".
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

// Each exemption is a deliberate design call; add one only with its reason.
const restrictedClassExemptions = [
	{
		// Display moments set in Unbounded (countdown, OTP digits, live counter, hero
		// title) and the bottom-nav labels, which step by width to fit «Голосование». The
		// hero's gradient is key art, so its palette stops are exempt too.
		files: [
			'src/routes/(app)/components/home/HeroCard.svelte',
			'src/routes/(app)/components/AppBottomNav.svelte',
			'src/routes/(app)/(protected)/tools/components/OnlineNowCard.svelte',
			'src/routes/(auth)/login/components/VerifyCodeForm.svelte',
			'src/routes/(app)/(protected)/profile/components/ChangeEmailForm.svelte'
		],
		rules: {
			'better-tailwindcss/no-restricted-classes': [
				'error',
				{ restrict: restrictedClasses('type', 'palette') }
			]
		}
	},
	{
		// Third-party brand marks (VK, Telegram, Svelte, FastAPI) and the footer heart
		// keep their own colours; a theme token would misstate the brand.
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
		// Tailwind class linting (eslint-plugin-better-tailwindcss; ADR-0030). The
		// recommended preset minus the two formatting rules prettier-plugin-tailwindcss
		// already owns: running both, they disagree on order and wrapping and fight.
		files: ['src/**/*.{svelte,ts,js}'],
		extends: [betterTailwindcss.configs['recommended-error']],
		settings: { 'better-tailwindcss': { entryPoint: 'src/app.css' } },
		rules: {
			'better-tailwindcss/enforce-consistent-class-order': 'off',
			'better-tailwindcss/enforce-consistent-line-wrapping': 'off',
			// The type roles share a size with a stock step (text-body is text-base's 1rem),
			// so canonicalisation would rewrite them back to the raw size and erase the role.
			// leading-* stays its own class: `text-sm leading-relaxed`, not `text-sm/relaxed`,
			// which is how docs/frontend.md writes the scale.
			'better-tailwindcss/enforce-canonical-classes': [
				'error',
				{ ignore: ['^(?:.*:)?text-(?:headline|section|body)$', '^(?:.*:)?leading-'] }
			],
			// Classes styled in a component's own <style> block, which the plugin can't see.
			'better-tailwindcss/no-unknown-classes': [
				'error',
				{ ignore: ['^toaster$', '^countdown-cell(--animated)?$', '^tick$'] }
			],
			'better-tailwindcss/no-restricted-classes': ['error', { restrict: restrictedClasses() }],
			// Outside the recommended preset: `p-2 p-4` on one element is always a slip.
			'better-tailwindcss/no-conflicting-classes': 'error'
		}
	},
	...restrictedClassExemptions,
	{
		// Vendored shadcn-svelte primitives: keep them diffable against upstream, so no
		// autofixing rewrites and none of the app's own design restrictions.
		files: ['src/lib/components/ui/**'],
		rules: {
			'better-tailwindcss/enforce-canonical-classes': 'off',
			'better-tailwindcss/no-deprecated-classes': 'off',
			'better-tailwindcss/no-duplicate-classes': 'off',
			'better-tailwindcss/no-restricted-classes': 'off'
		}
	},
	{
		// Tests build class names from data on purpose; nothing here reaches Tailwind's scanner.
		files: ['src/**/*.test.ts'],
		rules: { 'better-tailwindcss/no-concatenated-classes': 'off' }
	}
];
