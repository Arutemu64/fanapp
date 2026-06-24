<script lang="ts">
	import NotificationsFeed from './components/NotificationsFeed.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { feedSnapshotKey } from '$lib/utils/feed';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Remount the feed with the fresh server snapshot whenever route data changes.
	let notificationsKey = $derived(
		feedSnapshotKey(
			data.hasMore,
			data.notifications.map((notification) => notification.id)
		)
	);

	// Show the notice when the loaded copy is cached (data.stale) or the device went
	// offline since open — what's on screen may be out of date until reconnect. On an
	// offline cold miss there's no saved copy, so the dedicated empty state below
	// explains it instead.
	const offline = getOfflineService();
	let showStaleNotice = $derived(!data.offlineMiss && (data.stale || !offline.isOnline));
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
	<div
		class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
	>
		<p class="text-base font-bold text-gray-900 dark:text-white">Уведомления недоступны офлайн</p>
		<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
			Появятся после подключения к интернету
		</p>
	</div>
{:else}
	{#key notificationsKey}
		<NotificationsFeed initialNotifications={data.notifications} initialHasMore={data.hasMore} />
	{/key}
{/if}
