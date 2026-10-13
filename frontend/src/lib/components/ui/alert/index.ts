// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
import type { VariantProps } from 'class-variance-authority';

import { cva } from 'class-variance-authority';
export { default as Alert } from './Alert.vue';
export { default as Root } from './Alert.vue';
export { default as AlertAction } from './AlertAction.vue';
export { default as Action } from './AlertAction.vue';

export const alertVariants = cva(
	'grid gap-0.5 rounded-lg border px-4 py-3 text-left text-sm has-data-[slot=alert-action]:relative has-data-[slot=alert-action]:pr-18 has-[>svg]:grid-cols-[auto_1fr] has-[>svg]:gap-x-2.5 *:[svg]:row-span-2 *:[svg]:translate-y-0.5 *:[svg]:text-current *:[svg:not([class*=size-])]:size-4 group/alert relative w-full',
	{
		variants: {
			variant: {
				default: 'bg-card text-card-foreground',
				destructive:
					'text-destructive bg-card *:data-[slot=alert-description]:text-destructive/90 *:[svg]:text-current',
				// Signature tinted status notices (DESIGN.md §5 "Notices"): a soft /10 fill,
				// a /30 border and the status text colour, all mode-aware via the semantic
				// tokens so no `dark:` is needed. Lives here, not repeated per instance.
				// The description takes the full token, not the /90 the destructive variant
				// uses: on the tint, /90 drops light-mode text under AA's 4.5:1 (~3.8:1).
				success:
					'border-success/30 bg-success/10 text-success *:data-[slot=alert-description]:text-success',
				warning:
					'border-warning/30 bg-warning/10 text-warning *:data-[slot=alert-description]:text-warning',
				info: 'border-info/30 bg-info/10 text-info *:data-[slot=alert-description]:text-info'
			}
		},
		defaultVariants: {
			variant: 'default'
		}
	}
);

export type AlertVariants = VariantProps<typeof alertVariants>;
export type AlertVariant = AlertVariants['variant'];
export { default as AlertDescription } from './AlertDescription.vue';
export { default as Description } from './AlertDescription.vue';
export { default as AlertTitle } from './AlertTitle.vue';
export { default as Title } from './AlertTitle.vue';
