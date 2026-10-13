// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
import type { VariantProps } from 'class-variance-authority';

import { cva } from 'class-variance-authority';

export const fieldVariants = cva(
	'data-[invalid=true]:text-destructive gap-3 group/field flex w-full',
	{
		variants: {
			orientation: {
				vertical: 'flex-col *:w-full [&>.sr-only]:w-auto',
				horizontal:
					'flex-row items-center has-[>[data-slot=field-content]]:items-start *:data-[slot=field-label]:flex-auto has-[>[data-slot=field-content]]:[&>[role=checkbox],[role=radio]]:mt-px',
				responsive:
					'flex-col *:w-full @md/field-group:flex-row @md/field-group:items-center @md/field-group:*:w-auto @md/field-group:has-[>[data-slot=field-content]]:items-start @md/field-group:*:data-[slot=field-label]:flex-auto [&>.sr-only]:w-auto @md/field-group:has-[>[data-slot=field-content]]:[&>[role=checkbox],[role=radio]]:mt-px'
			}
		},
		defaultVariants: {
			orientation: 'vertical'
		}
	}
);

export type FieldVariants = VariantProps<typeof fieldVariants>;
export { default as Field } from './Field.vue';
export { default as FieldContent } from './FieldContent.vue';
export { default as Content } from './FieldContent.vue';
export { default as FieldDescription } from './FieldDescription.vue';
export { default as Description } from './FieldDescription.vue';
export { default as FieldError } from './FieldError.vue';
export { default as Error } from './FieldError.vue';
export { default as FieldGroup } from './FieldGroup.vue';
export { default as Group } from './FieldGroup.vue';
export { default as FieldLabel } from './FieldLabel.vue';
export { default as Label } from './FieldLabel.vue';
export { default as FieldLegend } from './FieldLegend.vue';
export { default as Legend } from './FieldLegend.vue';
export { default as FieldSeparator } from './FieldSeparator.vue';
export { default as Separator } from './FieldSeparator.vue';
export { default as FieldSet } from './FieldSet.vue';
export { default as Set } from './FieldSet.vue';
export { default as FieldTitle } from './FieldTitle.vue';
export { default as Title } from './FieldTitle.vue';
