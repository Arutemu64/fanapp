<script lang="ts">
	import { markNotificationsRead } from '$lib/api/generated';
	import {
		listUserNotificationsInfiniteOptions,
		listUserNotificationsQueryKey
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { offsetPagination } from '$lib/api/queries';
	import { offlineQueryOptions } from '$lib/api/queryClient';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { NOTIFICATION_PAGE_SIZE } from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService, shouldShowStaleNotice } from '$lib/services/offline.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createInfiniteQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const offline = getOfflineService();
	const queryClient = useQueryClient();

	const feedQuery = createInfiniteQuery(() => ({
		...listUserNotificationsInfiniteOptions({ query: { limit: NOTIFICATION_PAGE_SIZE } }),
		...offlineQueryOptions,
		...offsetPagination(NOTIFICATION_PAGE_SIZE, 'notifications')
	}));

	let notifications = $derived(feedQuery.data?.pages.flatMap((page) => page.notifications) ?? []);
	let unreadCount = $derived(notifications.filter((notification) => !notification.seen_at).length);

	// What's on screen came from the persisted copy after the live fetch failed.
	let servingCachedCopy = $derived(feedQuery.isError && feedQuery.data !== undefined);
	let offlineMiss = $derived(feedQuery.isError && feedQuery.data === undefined);
	let showStaleNotice = $derived(
		shouldShowStaleNotice({
			offlineMiss,
			stale: servingCachedCopy,
			isOnline: offline.isOnline
		})
	);

	// Every loaded page is refetched, so a notification that arrived while the SSE
	// stream was down lands in place rather than being appended out of order.
	function refreshFeed(): Promise<unknown> {
		return queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
	}

	function handleNewNotification(notification: Parameters<typeof toastService.push>[0]) {
		void refreshFeed();
		toastService.push(notification);
	}

	// Opening the page is the "mark-on-open" moment, but the first page arrives
	// after mount — so this waits for it and then runs exactly once per visit.
	let hasMarkedOnOpen = false;
	$effect(() => {
		if (hasMarkedOnOpen || !feedQuery.isSuccess) return;
		hasMarkedOnOpen = true;
		void markLoadedRead();
	});

	// Mark the currently-loaded unread items read on the server so the bell badge
	// clears when the user opens their notifications. Scoped to what was loaded at
	// that moment: later pages and live arrivals stay unread.
	async function markLoadedRead() {
		const unseenIds = notifications
			.filter((notification) => !notification.seen_at)
			.map((notification) => notification.id);
		if (unseenIds.length === 0) return;

		try {
			const { error, response } = await markNotificationsRead({
				body: { notification_ids: unseenIds }
			});
			if (!error && response?.ok) {
				await refreshFeed();
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	// Only a failed "load more" is worth a toast: a failed first page already shows
	// either the offline notice or the empty state below.
	$effect(() => {
		if (feedQuery.isError && feedQuery.data !== undefined) {
			toastService.error('Не удалось загрузить уведомления');
		}
	});

	onMount(() => {
		const reloadAfterReconnect = () => {
			void refreshFeed();
		};

		eventsClient.on('notification_created', handleNewNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', reloadAfterReconnect);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			eventsClient.off('connection_established', reloadAfterReconnect);
		};
	});
</script>

{#if showStaleNotice}
	<StaleDataNotice
		message="Нет связи. Показаны сохранённые уведомления — обновятся при подключении."
		cachedAt={feedQuery.dataUpdatedAt}
	/>
{/if}

<SectionIntro>
	{#if notifications.length > 0}
		<div class="text-sm text-muted-foreground">
			{#if unreadCount > 0}
				Непрочитанных: {unreadCount}
			{:else}
				Все уведомления прочитаны
			{/if}
		</div>
	{/if}
</SectionIntro>

{#if offlineMiss}
	<EmptyState
		title="Уведомления недоступны офлайн"
		message="Появятся после подключения к интернету"
	/>
{:else if notifications.length === 0}
	<EmptyState message="Уведомлений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each notifications as notification (notification.id)}
			<NotificationListItem {notification} />
		{/each}
	</div>

	{#if feedQuery.hasNextPage}
		<LoadMoreButton
			loading={feedQuery.isFetchingNextPage}
			onclick={() => feedQuery.fetchNextPage()}
		/>
	{/if}
{/if}
