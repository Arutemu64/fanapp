<script lang="ts">
	import { Button, Spinner } from 'flowbite-svelte';
	import { client } from '$lib/api';
	import type { components } from '$lib/api/v1';
	import { getToastService } from '$lib/services/toasts.svelte';
	import {
		NOTIFICATION_PAGE_REQUEST_LIMIT,
		NOTIFICATION_PAGE_SIZE
	} from '$lib/constants/notifications';
	import NotificationListItem from './NotificationListItem.svelte';
	import SectionHeader from '../SectionHeader.svelte';

	type Notification = components['schemas']['NotificationDTO'];

	interface Props {
		initialNotifications: Array<Notification>;
		initialHasMore: boolean;
	}

	let { initialNotifications, initialHasMore }: Props = $props();

	const toastService = getToastService();

	// Сервер отдает первую порцию, а в состоянии храним только то, что догрузили после нее.
	let extraNotifications = $state<Array<Notification>>([]);
	let extraHasMore = $state<boolean | null>(null);
	let extraOffset = $state(0);
	let isLoadingMore = $state(false);

	let notifications = $derived.by(() =>
		appendUniqueNotifications(initialNotifications, extraNotifications)
	);
	let hasMore = $derived(extraHasMore ?? initialHasMore);
	let nextOffset = $derived(initialNotifications.length + extraOffset);
	let unreadCount = $derived(notifications.filter((notification) => !notification.seen_at).length);

	function appendUniqueNotifications(
		existingNotifications: Array<Notification>,
		nextNotifications: Array<Notification>
	) {
		// Защищаемся от дублей, если список обновился между запросами.
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
</script>

<SectionHeader
	title="Уведомления"
	description="Здесь собраны все ваши уведомления. Новые сообщения находятся сверху."
>
	{#if notifications.length > 0}
		<div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
			{#if unreadCount > 0}
				Непрочитанных: {unreadCount}
			{:else}
				Все уведомления прочитаны
			{/if}
		</div>
	{/if}
</SectionHeader>

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
