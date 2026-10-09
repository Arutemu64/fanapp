<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { onMount } from 'svelte';

	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { feedSnapshotKey } from '#lib/utils/feed.js';

	import type { PageProps } from './$types';

	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';

	let { data }: PageProps = $props();

	const eventsClient = getEventsClient();

	// Re-seed the feed with the fresh first page after undo triggers invalidate().
	let changesKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.schedule_changes.map((change) => change.id)
		)
	);

	onMount(() => {
		// There is no dedicated SSE event for this feed: every change that adds a
		// row here (create, undo) also broadcasts 'schedule_updated', so that one
		// signal already fires on a superset of the moments this list goes stale.
		// The extra refetch it costs — a bulk import, which touches the schedule
		// but records no change row — is one request for the few staff on this page.
		// An event missed while the stream was down is caught by the reconnect
		// catch-up (reconnectRefresh), which re-runs this page's load.
		const reloadChanges = () => {
			void invalidate('app:schedule:changes');
		};

		eventsClient.on('schedule_updated', reloadChanges);

		return () => {
			eventsClient.off('schedule_updated', reloadChanges);
		};
	});
</script>

<svelte:head>
	<title>Изменения программы · ФАН ФАН</title>
</svelte:head>

{#key changesKey}
	<ScheduleChangesFeed initialChanges={data.schedule_changes} initialHasMore={data.hasMore} />
{/key}
