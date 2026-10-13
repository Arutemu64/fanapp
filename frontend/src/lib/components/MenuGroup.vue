<script setup lang="ts">
import { cn } from '#lib/utils.js';

defineProps<{ class?: string }>();
</script>

<!-- One bordered block per group of rows: the grouped-list shape of a phone's
     settings screen. It sits straight on the page, never inside a Card, so related
     rows read as one set rather than as boxes-inside-a-box — and the /profile hub
     stays short enough that logout sits about a screen down instead of under a
     stack of cards. -->
<template>
	<div :class="cn('overflow-hidden rounded-2xl border border-border bg-card', $props.class)">
		<slot />
	</div>
</template>
