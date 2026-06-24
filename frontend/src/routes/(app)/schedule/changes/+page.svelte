<script lang="ts">
	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Re-seed the feed with the fresh first page after undo triggers invalidate().
	let changesKey = $derived(
		`${data.hasMore}:${data.schedule_changes.map((change) => change.id).join(':')}`
	);
</script>

<svelte:head>
	<title>Изменения программы · ФАН ФАН</title>
</svelte:head>

{#key changesKey}
	<ScheduleChangesFeed initialChanges={data.schedule_changes} initialHasMore={data.hasMore} />
{/key}
