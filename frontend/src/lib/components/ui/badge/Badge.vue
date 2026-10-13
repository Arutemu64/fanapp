<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui';
import type { HTMLAttributes } from 'vue';

import { Primitive } from 'reka-ui';
import { computed } from 'vue';

import { cn } from '#lib/utils.js';

import type { BadgeVariants } from '.';

import { badgeVariants } from '.';

const props = defineProps<
	PrimitiveProps & {
		variant?: BadgeVariants['variant'];
		class?: HTMLAttributes['class'];
		/** Renders an `<a>` instead of a `<span>`. */
		href?: string;
	}
>();

const tag = computed(() => props.as ?? (props.href === undefined ? 'span' : 'a'));
</script>

<template>
	<Primitive
		data-slot="badge"
		:data-variant="variant"
		:as="tag"
		:as-child="asChild"
		:href="href"
		:class="cn(badgeVariants({ variant }), props.class)"
	>
		<slot />
	</Primitive>
</template>
