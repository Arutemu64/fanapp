<script lang="ts">
	import * as Alert from '$lib/components/ui/alert';
	import { formatSyncedAt } from '$lib/utils/formatters';
	import { Clock } from '@lucide/svelte';

	// Shown when a page is rendering a cached copy because the network was down.
	let {
		message = 'Нет связи. Показаны сохранённые данные — обновятся при подключении.',
		cachedAt
	}: {
		message?: string;
		// Epoch millis of when the shown copy was cached; adds a "synced at" line.
		cachedAt?: number;
	} = $props();

	let syncedLabel = $derived(cachedAt !== undefined ? formatSyncedAt(cachedAt) : undefined);
</script>

<Alert.Root variant="warning">
	<Clock />
	<Alert.Description>
		{message}
		{#if syncedLabel}
			<span class="mt-0.5 block text-xs opacity-80">Синхронизировано {syncedLabel}</span>
		{/if}
	</Alert.Description>
</Alert.Root>
