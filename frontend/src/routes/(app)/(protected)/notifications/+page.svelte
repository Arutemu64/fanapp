<script lang="ts">
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
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

	const offline = getOfflineService();
	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss: data.offlineMiss,
			stale: data.stale,
			isOnline: offline.isOnline
		})
	);
</script>

<svelte:head>
	<title>Уведомления · ФАН ФАН</title>
</svelte:head>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые уведомления — обновятся при подключении."
		cachedAt={data.cachedAt}
	/>
{/if}

{#if data.offlineMiss}
	<EmptyState
		title="Уведомления недоступны офлайн"
		message="Появятся после подключения к интернету"
	/>
{:else}
	{#key notificationsKey}
		<NotificationsFeed initialNotifications={data.notifications} initialHasMore={data.hasMore} />
	{/key}
{/if}
