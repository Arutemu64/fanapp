<script lang="ts">
	import { Button, Spinner } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { createApiClient } from '$lib/api';
	import type { NotificationDTO } from '$lib/types/notifications';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '$lib/constants/notifications';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';

	const client = createApiClient();

	interface Props {
		initialNotifications: Array<NotificationDTO>;
		initialHasMore: boolean;
	}

	let { initialNotifications, initialHasMore }: Props = $props();

	const toastService = getToastService();
	const eventsClient = getEventsClient();

	// Server provides the first page; state holds only pages loaded afterwards.
	let extraNotifications = $state.raw<Array<NotificationDTO>>([]);
	let extraHasMore = $state<boolean | null>(null);
	let extraOffset = $state(0);
	let isLoadingMore = $state(false);
	// Notifications pushed over SSE — kept on top, newest first.
	let liveNotifications = $state.raw<Array<NotificationDTO>>([]);

	let notifications = $derived.by(() => {
		// Order: fresh SSE items on top, then the server page and anything loaded after it.
		const serverNotifications = appendUniqueNotifications(initialNotifications, extraNotifications);
		return appendUniqueNotifications(liveNotifications, serverNotifications);
	});
	let hasMore = $derived(extraHasMore ?? initialHasMore);
	let nextOffset = $derived(initialNotifications.length + extraOffset);
	let unreadCount = $derived(notifications.filter((notification) => !notification.seen_at).length);

	function appendUniqueNotifications(
		existingNotifications: Array<NotificationDTO>,
		nextNotifications: Array<NotificationDTO>
	) {
		// Guard against duplicates if the list shifted between requests.
		const existingIds = new Set(existingNotifications.map((notification) => notification.id));

		return [
			...existingNotifications,
			...nextNotifications.filter((notification) => !existingIds.has(notification.id))
		];
	}

	async function loadMoreNotifications() {
		if (!hasMore || isLoadingMore) {
			return;
		}

		isLoadingMore = true;

		try {
			const { data: result, error } = await client.GET('/notifications/', {
				params: {
					query: {
						limit: NOTIFICATION_PAGE_REQUEST_LIMIT,
						offset: nextOffset
					}
				}
			});

			if (error || !result) {
				toastService.error('Не удалось загрузить уведомления');
				return;
			}

			const nextNotifications = result.notifications.slice(0, NOTIFICATION_PAGE_SIZE);

			extraNotifications = appendUniqueNotifications(extraNotifications, nextNotifications);
			extraHasMore = result.notifications.length > NOTIFICATION_PAGE_SIZE;
			extraOffset += nextNotifications.length;
		} catch (error) {
			console.error('Failed to load more notifications', error);
			toastService.error('Не удалось загрузить уведомления');
		} finally {
			isLoadingMore = false;
		}
	}

	function addLiveNotification(notification: NotificationDTO) {
		liveNotifications = appendUniqueNotifications([notification], liveNotifications);
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

			const knownIds = new Set(
				[...initialNotifications, ...extraNotifications].map((notification) => notification.id)
			);
			const fresh = result.notifications.filter((notification) => !knownIds.has(notification.id));
			liveNotifications = appendUniqueNotifications(fresh, liveNotifications);
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
	<div
		class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800"
	>
		<p class="text-gray-500 dark:text-gray-400">Уведомлений пока нет</p>
	</div>
{:else}
	<div class="space-y-3">
		{#each notifications as notification (notification.id)}
			<NotificationListItem {notification} />
		{/each}
	</div>

	{#if hasMore}
		<div class="mt-4 flex justify-center">
			<Button
				color="light"
				class="w-full sm:w-auto"
				onclick={loadMoreNotifications}
				disabled={isLoadingMore}
			>
				{#if isLoadingMore}
					<Spinner size="4" class="me-2" />
				{/if}
				{isLoadingMore ? 'Загрузка…' : 'Показать ещё'}
			</Button>
		</div>
	{/if}
{/if}
