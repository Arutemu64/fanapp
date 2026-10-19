<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';

	import * as Alert from '#lib/components/ui/alert/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { reachability } from '#lib/services/reachability.js';
	import { formatSyncedAt } from '#lib/utils/formatters.js';

	// Shown when a page is rendering a cached copy: the server is out of reach, or
	// it answered the last refetch with an error.
	//
	// Quiet first, loud once the copy is old enough to mislead. In a region where
	// mobile internet is cut for hours, offline is the normal state rather than an
	// alarm, and the connection banner already says so: a warning box on top of it
	// for every glance is noise people learn to skip. So a fresh copy gets one muted
	// "updated at" line, and only a copy past LOUD_AFTER_MS becomes the warning,
	// with what happens next — timestamps sparingly, escalating when the data is
	// old enough to matter (Google's offline & sync guidelines,
	// https://developers.google.com/open-health-stack/design/offline-sync-guideline).
	let {
		message = m.stale_data_default(),
		cachedAt
	}: {
		/** What is on screen, e.g. «Показана сохранённая программа.». No cause: the
		 *  connection banner already names it, and the notice adds what happens next. */
		message?: string;
		/** Epoch millis of when the shown copy was fetched. */
		cachedAt: number;
	} = $props();

	// A tuning knob: about six to ten acts at the festival's pace, past which a
	// saved programme or leaderboard has likely moved under the attendee.
	const LOUD_AFTER_MS = 30 * 60 * 1000;

	let loud = $derived(minuteClock.now - cachedAt >= LOUD_AFTER_MS);
	// Worded without a subject so one line fits every page despite Russian
	// agreement. Reachable means the server answered the refetch with an error, so
	// "when connected" would blame a connection that is fine.
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
