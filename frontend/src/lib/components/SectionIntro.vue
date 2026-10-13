<script setup lang="ts">
defineProps<{
	/** Optional description (p) shown under the navbar page title */
	description?: string;
}>();
</script>

<!-- The page title lives in the navbar; this only renders the optional
	intro text/extra content (default slot) for screens that need extra context. -->
<template>
	<div v-if="description || $slots.default" class="mb-4 sm:mb-6">
		<p v-if="description" class="text-base leading-relaxed text-muted-foreground">
			{{ description }}
		</p>
		<slot />
	</div>
</template>
