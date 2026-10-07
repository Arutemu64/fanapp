<script lang="ts">
	import { feedSnapshotKey } from '$lib/utils/feed';

	import type { PageProps } from './$types';

	import NotificationsFeed from './components/NotificationsFeed.svelte';

	let { data }: PageProps = $props();

	// Remount the feed with the fresh server snapshot whenever route data changes.
	let notificationsKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.notifications.map((notification) => notification.id)
		)
	);
</script>

<svelte:head>
	<title>Уведомления · ФАН ФАН</title>
</svelte:head>

{#key notificationsKey}
	<NotificationsFeed initialNotifications={data.notifications} initialHasMore={data.hasMore} />
{/key}
