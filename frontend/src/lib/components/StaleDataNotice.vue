<script setup lang="ts">
import { Clock } from '@lucide/vue';
import { computed } from 'vue';

import * as Alert from '#lib/components/ui/alert/index.js';
import { formatSyncedAt } from '#lib/utils/formatters.js';

// Shown when a page is rendering a cached copy because the network was down.
const {
	message = 'Нет связи. Показаны сохранённые данные — обновятся при подключении.',
	cachedAt
} = defineProps<{
	message?: string;
	// Epoch millis of when the shown copy was cached; adds a "synced at" line.
	cachedAt?: number;
}>();

const syncedLabel = computed(() => (cachedAt === undefined ? undefined : formatSyncedAt(cachedAt)));
</script>

<template>
	<Alert.Root variant="warning">
		<Clock />
		<Alert.Description>
			{{ message }}
			<span v-if="syncedLabel" class="mt-0.5 block text-xs opacity-80"
				>Синхронизировано {{ syncedLabel }}</span
			>
		</Alert.Description>
	</Alert.Root>
</template>
