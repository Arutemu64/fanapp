<script lang="ts">
	import { notificationsFeedOptions } from '$lib/api/feeds';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { createInfiniteQuery } from '@tanstack/svelte-query';

	import NotificationsFeed from './components/NotificationsFeed.svelte';

	const offline = getOfflineService();

	// Same key as the feed's own query, so this is a read of that cache entry and
	// never a second request — it only supplies the "synced at" timestamp and tells
	// an offline cold miss (nothing saved) from offline-with-saved-data.
	const feed = createInfiniteQuery(() => notificationsFeedOptions());

	let hasCachedData = $derived((feed.data?.pages.length ?? 0) > 0);
	let offlineMiss = $derived(!offline.isOnline && !hasCachedData);
	let showStaleNotice = $derived(!offline.isOnline && hasCachedData);
</script>

<svelte:head>
	<title>Уведомления · ФАН ФАН</title>
</svelte:head>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые уведомления — обновятся при подключении."
		cachedAt={feed.dataUpdatedAt}
	/>
{/if}

{#if offlineMiss}
	<EmptyState
		title="Уведомления недоступны офлайн"
		message="Появятся после подключения к интернету"
	/>
{:else}
	<NotificationsFeed />
{/if}
