<script lang="ts">
	import type { NotificationDto } from '$lib/api/generated';

	import {
		countUnreadNotificationsQueryKey,
		listUserNotificationsInfiniteOptions,
		listUserNotificationsQueryKey,
		markNotificationsReadMutation
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { flattenPages, offsetPageParams } from '$lib/api/pagination';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { createInfiniteQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';

	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const queryClient = useQueryClient();

	const feed = createInfiniteQuery(() => ({
		...listUserNotificationsInfiniteOptions({
			query: { limit: NOTIFICATION_PAGE_REQUEST_LIMIT }
		}),
		...offsetPageParams(
			(page: { notifications: Array<NotificationDto> }) => page.notifications,
			NOTIFICATION_PAGE_SIZE
		)
	}));

	let notifications = $derived(
		flattenPages(feed.data?.pages, (page) => page.notifications, NOTIFICATION_PAGE_SIZE)
	);

	const markRead = createMutation(() => markNotificationsReadMutation());

	// Opening the page marks the items already loaded as read (mark-on-open). We
	// don't mutate the fetched DTOs — they still carry seen_at: null — so overlay
	// the read state locally: their "new" dots clear and the header settles without
	// waiting for a refetch. On the next visit the server returns them seen.
	let locallyReadIds = new SvelteSet<NotificationDto['id']>();
	const readAt = new Date().toISOString();
	let displayNotifications = $derived(
		notifications.map((notification) =>
			notification.seen_at || !locallyReadIds.has(notification.id)
				? notification
				: { ...notification, seen_at: readAt }
		)
	);
	let unreadCount = $derived(
		displayNotifications.filter((notification) => !notification.seen_at).length
	);

	// Mark the currently-loaded unread items read on the server so the bell badge
	// clears when the user opens their notifications, then reconcile the shared
	// count. Scoped to what's loaded now: later pages and live arrivals stay unread.
	async function markLoadedRead() {
		const unseenIds = notifications
			.filter((notification) => !notification.seen_at)
			.map((notification) => notification.id);
		if (unseenIds.length === 0) return;

		try {
			await markRead.mutateAsync({ body: { notification_ids: unseenIds } });
			for (const id of unseenIds) {
				locallyReadIds.add(id);
			}
			// The bell's preview and badge read the same data from their own keys.
			void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
			void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	// Refetch every loaded page rather than splicing the SSE payload in at the top:
	// a notification can arrive while pages are still loading, and the server's
	// ordering is the only one that stays correct across pagination. On reconnect
	// this also picks up anything published while the stream was down.
	function refetchFeed() {
		void queryClient.invalidateQueries({
			queryKey: listUserNotificationsInfiniteOptions({
				query: { limit: NOTIFICATION_PAGE_REQUEST_LIMIT }
			}).queryKey
		});
	}

	function handleNewNotification(notification: NotificationDto) {
		refetchFeed();
		toastService.push(notification);
	}

	onMount(() => {
		// Opening the page is the "mark-on-open" moment for the items on screen.
		void markLoadedRead();

		eventsClient.on('notification_created', handleNewNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', refetchFeed);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			eventsClient.off('connection_established', refetchFeed);
		};
	});
</script>

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

{#if displayNotifications.length === 0}
	<EmptyState message="Уведомлений пока нет" />
{:else}
	<div class="flex flex-col gap-3">
		{#each displayNotifications as notification (notification.id)}
			<NotificationListItem {notification} />
		{/each}
	</div>

	{#if feed.hasNextPage}
		<LoadMoreButton loading={feed.isFetchingNextPage} onclick={() => feed.fetchNextPage()} />
	{/if}
{/if}
