<script lang="ts">
	import { ClockOutline } from 'flowbite-svelte-icons';
	import NoticeCallout from './NoticeCallout.svelte';
	import { formatSyncedAt } from '$lib/utils/formatters';

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

{#if syncedLabel}
	<NoticeCallout tone="warning" icon={ClockOutline} role="status">
		{message}
		<span class="mt-0.5 block text-xs opacity-80">Синхронизировано {syncedLabel}</span>
	</NoticeCallout>
{:else}
	<NoticeCallout tone="warning" icon={ClockOutline} {message} role="status" />
{/if}
