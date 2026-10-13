<script setup lang="ts">
import type { HTMLAttributes } from 'vue';

import { reactiveOmit } from '@vueuse/core';
import { useForwardProps } from 'reka-ui';
import { computed } from 'vue';
import { useVueOTPContext } from 'vue-input-otp';

import { cn } from '#lib/utils.js';

const props = defineProps<{ index: number; class?: HTMLAttributes['class'] }>();

const delegatedProps = reactiveOmit(props, 'class');

const forwarded = useForwardProps(delegatedProps);

const context = useVueOTPContext();

const slot = computed(() => context?.value.slots[props.index]);
</script>

<template>
	<div
		v-bind="forwarded"
		data-slot="input-otp-slot"
		:data-active="slot?.isActive"
		:class="
			cn(
				// Signature OTP box: 44px tap target (h-11) with a large bold digit, sm:h-12 on
				// desktop (DESIGN.md §5, OTP). Deviates from the vega default (size-9 text-sm) —
				// keep on a shadcn-vue update.
				'relative flex h-11 w-11 items-center justify-center border-y border-r border-input text-lg font-bold transition-all outline-none first:rounded-l-md first:border-l last:rounded-r-md aria-invalid:border-destructive sm:h-12 dark:bg-input/30',
				'data-[active=true]:z-10 data-[active=true]:border-ring data-[active=true]:ring-3 data-[active=true]:ring-ring/50 data-[active=true]:aria-invalid:border-destructive data-[active=true]:aria-invalid:ring-destructive/20 dark:data-[active=true]:aria-invalid:ring-destructive/40',
				props.class
			)
		"
	>
		{{ slot?.char }}
		<div
			v-if="slot?.hasFakeCaret"
			class="pointer-events-none absolute inset-0 flex items-center justify-center"
		>
			<div class="h-4 w-px animate-caret-blink bg-foreground duration-1000" />
		</div>
	</div>
</template>
