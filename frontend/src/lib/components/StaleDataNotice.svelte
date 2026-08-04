<script lang="ts">
	import { formatSyncedAt } from '$lib/utils/formatters';
	import { Alert } from 'flowbite-svelte';
	import { ClockOutline } from 'flowbite-svelte-icons';

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

<Alert color="yellow" class="rounded-xl">
	{#snippet icon()}
		<ClockOutline class="h-5 w-5 shrink-0" />
	{/snippet}
	{message}
	{#if syncedLabel}
		<span class="mt-0.5 block text-xs opacity-80">Синхронизировано {syncedLabel}</span>
	{/if}
</Alert>
