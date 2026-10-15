<script lang="ts">
	import { Clock } from '@lucide/svelte';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { formatSyncedAt } from '#lib/utils/formatters.js';

	// Shown when a page is rendering a cached copy: the server is out of reach, or
	// it answered the last refetch with an error.
	let {
		message = m.stale_data_default(),
		cachedAt
	}: {
		/** What is on screen, e.g. «Показана сохранённая программа.». No cause: the
		 *  connection banner already names it, and the notice adds what happens next. */
		message?: string;
		// Epoch millis of when the shown copy was cached; adds a "synced at" line.
		cachedAt?: number;
	} = $props();

	// Worded without a subject so one line fits every page despite Russian
	// agreement. Reachable means the server answered the refetch with an error, so
	// "when connected" would blame a connection that is fine.
	let nextStep = $derived(
		reachability.current ? m.stale_data_retry_later() : m.stale_data_refresh_on_reconnect()
	);
	let syncedLabel = $derived(cachedAt !== undefined ? formatSyncedAt(cachedAt) : undefined);
</script>

<Alert.Root variant="warning">
	<Clock />
	<Alert.Description>
		{message}
		{nextStep}
		{#if syncedLabel}
			<span class="mt-0.5 block text-xs opacity-80">{m.stale_data_synced({ syncedLabel })}</span>
		{/if}
	</Alert.Description>
</Alert.Root>
