<script lang="ts">
	import type { NotificationDTO } from '$lib/types/notifications';

	import { createApiClient } from '$lib/api';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadMoreButton from '$lib/components/LoadMoreButton.svelte';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { PaginatedFeed } from '$lib/services/feed.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { getUnreadCountService } from '$lib/services/unreadCount.svelte';
	import { dedupeById } from '$lib/utils/feed';
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';

	const client = createApiClient();

	interface Props {
		initialNotifications: Array<NotificationDTO>;
		initialHasMore: boolean;
	}

	let { initialNotifications, initialHasMore }: Props = $props();

	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const unread = getUnreadCountService();

	const feed = new PaginatedFeed<NotificationDTO>({
		pageSize: NOTIFICATION_PAGE_SIZE,
		requestLimit: NOTIFICATION_PAGE_REQUEST_LIMIT,
		getInitialItems: () => initialNotifications,
		getInitialHasMore: () => initialHasMore,
		fetchPage: async (limit, offset) => {
			const { data, error } = await client.GET('/notifications/', {
				params: { query: { limit, offset } }
			});
			return error || !data ? null : data.notifications;
		},
		onError: () => toastService.error('Не удалось загрузить уведомления')
	});

	// Notifications pushed over SSE — kept on top, newest first.
	let liveNotifications = $state.raw<Array<NotificationDTO>>([]);

	// Fresh SSE items on top, then the server page and anything loaded after it.
	let notifications = $derived(dedupeById(liveNotifications, feed.items));

	// Opening the page marks the items already loaded as read (mark-on-open). We
	// don't mutate the fetched DTOs — they still carry seen_at: null — so overlay
	// the read state locally: their "new" dots clear and the header settles without
	// waiting for a refetch. On the next visit the server returns them seen.
	let locallyReadIds = new SvelteSet<NotificationDTO['id']>();
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

	function addLiveNotification(notification: NotificationDTO) {
		liveNotifications = dedupeById([notification], liveNotifications);
		toastService.push(notification);
	}

	// Mark the currently-loaded unread items read on the server so the bell badge
	// clears when the user opens their notifications, then reconcile the shared
	// count. Scoped to what's loaded now: later pages and live arrivals stay unread.
	async function markLoadedRead() {
		const unseenIds = notifications
			.filter((notification) => !notification.seen_at)
			.map((notification) => notification.id);
		if (unseenIds.length === 0) return;

		try {
			const { error, response } = await client.POST('/notifications/mark-read', {
				body: { notification_ids: unseenIds }
			});
			if (!error && response.ok) {
				for (const id of unseenIds) {
					locallyReadIds.add(id);
				}
				await unread.refresh();
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	// Refetch the first page and lift anything not yet in the list to the top, so we
	// don't lose notifications that arrived while the SSE channel was disconnected.
	async function syncLatestNotifications() {
		try {
			const { data: result, error } = await client.GET('/notifications/', {
				params: { query: { limit: NOTIFICATION_PAGE_SIZE } }
			});

			if (error || !result) {
				return;
			}

			const knownIds = new Set(feed.items.map((notification) => notification.id));
			const fresh = result.notifications.filter((notification) => !knownIds.has(notification.id));
			liveNotifications = dedupeById(fresh, liveNotifications);
		} catch (error) {
			console.error('Failed to sync notifications', error);
		}
	}

	function syncAfterReconnect() {
		void syncLatestNotifications();
	}

	onMount(() => {
		// Opening the page is the "mark-on-open" moment for the items on screen.
		void markLoadedRead();

		eventsClient.on('notification_created', addLiveNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', syncAfterReconnect);

		return () => {
			eventsClient.off('notification_created', addLiveNotification);
			eventsClient.off('connection_established', syncAfterReconnect);
		};
	});
</script>

<SectionIntro>
	{#if notifications.length > 0}
		<div class="text-sm text-gray-500 dark:text-gray-400">
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
	<div class="space-y-3">
		{#each displayNotifications as notification (notification.id)}
			<NotificationListItem {notification} />
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
