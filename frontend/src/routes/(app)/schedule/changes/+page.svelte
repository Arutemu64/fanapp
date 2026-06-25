<script lang="ts">
	import { feedSnapshotKey } from '$lib/utils/feed';

	import type { PageProps } from './$types';

	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';

	let { data }: PageProps = $props();

	// Re-seed the feed with the fresh first page after undo triggers invalidate().
	let changesKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.schedule_changes.map((change) => change.id)
		)
	);
</script>

<svelte:head>
	<title>Изменения программы · ФАН ФАН</title>
</svelte:head>

{#key changesKey}
	<ScheduleChangesFeed initialChanges={data.schedule_changes} initialHasMore={data.hasMore} />
{/key}
