<script setup lang="ts">
import { Button } from '#lib/components/ui/button/index.js';
import { Spinner } from '#lib/components/ui/spinner/index.js';

defineProps<{
	// The next page is loading: shows the spinner.
	loading: boolean;
	// Any fetch of the list is running. A background refetch rewrites every
	// loaded page, and fetching the next one meanwhile can overwrite it
	// (https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries).
	busy: boolean;
}>();

// Emits `click` rather than a callback prop; a bare `@click` on the component
// would fall through to the root div and fire for taps next to the button too.
defineEmits<{ click: [] }>();
</script>

<template>
	<div class="mt-4 flex justify-center">
		<Button variant="outline" class="w-full sm:w-auto" :disabled="busy" @click="$emit('click')">
			<Spinner v-if="loading" data-icon="inline-start" />
			{{ loading ? 'Загрузка…' : 'Показать ещё' }}
		</Button>
	</div>
</template>
