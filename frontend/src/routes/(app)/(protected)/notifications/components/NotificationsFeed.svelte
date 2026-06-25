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
	import { getToastService } from '$lib/services/toasts.svelte';
	import { dedupeById } from '$lib/utils/feed';
	import { PaginatedFeed } from '$lib/utils/feed.svelte';
	import { onMount } from 'svelte';

	const client = createApiClient();

	interface Props {
		initialNotifications: Array<NotificationDTO>;
		initialHasMore: boolean;
	}

	let { initialNotifications, initialHasMore }: Props = $props();

	const toastService = getToastService();
	const eventsClient = getEventsClient();

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
	let unreadCount = $derived(notifications.filter((notification) => !notification.seen_at).length);

	function addLiveNotification(notification: NotificationDTO) {
		liveNotifications = dedupeById([notification], liveNotifications);
		toastService.push(notification);
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
		if (!eventsClient) {
			return;
		}

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

{#if notifications.length === 0}
	<EmptyState message="Уведомлений пока нет" />
{:else}
	<div class="space-y-3">
		{#each notifications as notification (notification.id)}
			<NotificationListItem {notification} />
		{/each}
	</div>

	{#if feed.hasMore}
		<LoadMoreButton loading={feed.isLoadingMore} onclick={feed.loadMore} />
	{/if}
{/if}
