<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { reachability } from '#lib/services/reachability.js';
	import { formatSyncedAt } from '#lib/utils/formatters.js';

	let {
		message = m.stale_data_default(),
		cachedAt
	}: {
		message?: string;
		cachedAt: number;
	} = $props();

	const LOUD_AFTER_MS = 30 * 60 * 1000;

	let loud = $derived(minuteClock.now - cachedAt >= LOUD_AFTER_MS);
	let nextStep = $derived(
		reachability.current ? m.stale_data_retry_later() : m.stale_data_refresh_on_reconnect()
	);
	let syncedLabel = $derived(formatSyncedAt(cachedAt));
</script>

{#if loud}
	<Alert.Root variant="warning">
		<Clock />
		<Alert.Description>
			{message}
			{nextStep}
			<span class="mt-0.5 block text-xs opacity-80">{m.stale_data_synced({ syncedLabel })}</span>
		</Alert.Description>
	</Alert.Root>
{:else}
	<p class="flex items-center gap-1.5 text-xs text-muted-foreground">
		<Clock class="size-3.5 shrink-0" aria-hidden="true" />
		{m.stale_data_updated({ syncedLabel })}
	</p>
{/if}
