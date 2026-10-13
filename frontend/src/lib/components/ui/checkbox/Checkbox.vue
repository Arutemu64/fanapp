<script setup lang="ts">
import type { CheckboxRootEmits, CheckboxRootProps } from 'reka-ui';
import type { HTMLAttributes } from 'vue';

import { CheckIcon } from '@lucide/vue';
import { reactiveOmit } from '@vueuse/core';
import { CheckboxIndicator, CheckboxRoot, useForwardPropsEmits } from 'reka-ui';

import { cn } from '#lib/utils.js';

const props = defineProps<CheckboxRootProps & { class?: HTMLAttributes['class'] }>();
const emits = defineEmits<CheckboxRootEmits>();

const delegatedProps = reactiveOmit(props, 'class');

const forwarded = useForwardPropsEmits(delegatedProps, emits);
</script>

<template>
	<!--
    The `after:` pseudo extends the tap target beyond the 16px visual box (which is
    under the WCAG 2.2 AA 24px minimum) without changing the layout — same technique
    as `Switch.vue`. `relative` anchors the pseudo to the box. Deviates from the
    upstream shadcn checkbox; keep it on a shadcn-vue update merge.
  -->
	<CheckboxRoot
		v-slot="slotProps"
		data-slot="checkbox"
		v-bind="forwarded"
		:class="
			cn(
				'peer relative flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-input shadow-xs transition-shadow outline-none group-has-disabled/field:opacity-50 after:absolute after:-inset-x-3 after:-inset-y-2 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 aria-invalid:aria-checked:border-primary dark:bg-input/30 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 data-checked:border-primary data-checked:bg-primary data-checked:text-primary-foreground dark:data-checked:bg-primary',
				props.class
			)
		"
	>
		<CheckboxIndicator
			data-slot="checkbox-indicator"
			class="grid place-content-center text-current transition-none [&>svg]:size-3.5"
		>
			<slot v-bind="slotProps">
				<CheckIcon />
			</slot>
		</CheckboxIndicator>
	</CheckboxRoot>
</template>
