<script setup lang="ts">
import type { HTMLAttributes } from 'vue';

import { computed } from 'vue';

import { cn } from '#lib/utils.js';

import type { AlertVariants } from '.';

import { alertVariants } from '.';

const props = defineProps<{
	class?: HTMLAttributes['class'];
	variant?: AlertVariants['variant'];
}>();

// Only an error interrupts the screen reader (assertive `alert`); a success,
// warning or info notice is advisory, so it waits its turn (polite `status`).
// https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/status_role
// Deviates from vega defaults — keep on a shadcn-vue update. A caller's own
// `role` attribute still wins, since fallthrough attributes are merged after this one.
const role = computed(() => (props.variant === 'destructive' ? 'alert' : 'status'));
</script>

<template>
	<div data-slot="alert" :role="role" :class="cn(alertVariants({ variant }), props.class)">
		<slot />
	</div>
</template>
