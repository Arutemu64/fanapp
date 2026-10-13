// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
import type { VariantProps } from 'class-variance-authority';

import { cva } from 'class-variance-authority';
export { default as Empty } from './Empty.vue';
export { default as Root } from './Empty.vue';
export { default as EmptyContent } from './EmptyContent.vue';
export { default as Content } from './EmptyContent.vue';
export { default as EmptyDescription } from './EmptyDescription.vue';
export { default as Description } from './EmptyDescription.vue';

export const emptyMediaVariants = cva(
	'mb-2 flex shrink-0 items-center justify-center [&_svg]:pointer-events-none [&_svg]:shrink-0',
	{
		variants: {
			variant: {
				default: 'bg-transparent',
				icon: 'bg-muted text-foreground flex size-10 shrink-0 items-center justify-center rounded-lg [&_svg:not([class*=size-])]:size-6'
			}
		},
		defaultVariants: {
			variant: 'default'
		}
	}
);

export type EmptyMediaVariants = VariantProps<typeof emptyMediaVariants>;
export { default as EmptyHeader } from './EmptyHeader.vue';
export { default as Header } from './EmptyHeader.vue';
export { default as EmptyMedia } from './EmptyMedia.vue';
export { default as Media } from './EmptyMedia.vue';
export { default as EmptyTitle } from './EmptyTitle.vue';
export { default as Title } from './EmptyTitle.vue';
