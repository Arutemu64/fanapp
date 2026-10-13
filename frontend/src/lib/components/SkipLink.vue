<script setup lang="ts">
const { targetId = 'main-content', label = 'Перейти к содержимому' } = defineProps<{
	targetId?: string;
	label?: string;
}>();

function skipToContent() {
	const target = document.getElementById(targetId);

	if (!(target instanceof HTMLElement)) {
		return;
	}

	target.focus();
	target.scrollIntoView({ block: 'start' });
}
</script>

<template>
	<button
		type="button"
		class="pointer-events-none absolute top-3 left-3 z-(--z-overlay) -translate-y-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white opacity-0 shadow-lg transition-[opacity,transform] focus:outline-none focus-visible:pointer-events-auto focus-visible:translate-y-0 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-primary-600"
		@click="skipToContent"
	>
		{{ label }}
	</button>
</template>
