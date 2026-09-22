<script lang="ts">
	import { listScheduleChangesInfiniteOptions } from '$lib/api/generated/@tanstack/svelte-query.gen';
	import BackLink from '$lib/components/BackLink.svelte';
	import { SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT } from '$lib/constants/schedule_changes';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import ScheduleChangesFeed from './components/ScheduleChangesFeed.svelte';

	const eventsClient = getEventsClient();
	const queryClient = useQueryClient();

	onMount(() => {
		// There is no dedicated SSE event for this feed: every change that adds a
		// row here (create, undo) also broadcasts 'schedule_updated', so that one
		// signal already fires on a superset of the moments this list goes stale.
		// The extra refetch it costs — a bulk import, which touches the schedule
		// but records no change row — is one request for the few staff on this page.
		// Also refetch on (re)connect, so an event missed while the stream was down
		// doesn't leave another staffer's edit invisible here.
		const reloadChanges = () => {
			void queryClient.invalidateQueries({
				queryKey: listScheduleChangesInfiniteOptions({
					query: { limit: SCHEDULE_CHANGES_PAGE_REQUEST_LIMIT }
				}).queryKey
			});
		};

		eventsClient.on('schedule_updated', reloadChanges);
		eventsClient.on('connection_established', reloadChanges);

		return () => {
			eventsClient.off('schedule_updated', reloadChanges);
			eventsClient.off('connection_established', reloadChanges);
		};
	});
</script>

<svelte:head>
	<title>Изменения программы · ФАН ФАН</title>
</svelte:head>

<BackLink href="/schedule" label="Назад к программе" />

<ScheduleChangesFeed />
