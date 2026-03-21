<script lang="ts">
	import { resolve } from '$app/paths';
	import { client } from '$lib/api';
	import type { components } from '$lib/api/v1';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import { NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
	import { Dropdown } from 'flowbite-svelte';
	import { BellSolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';
	import { getEventsClient } from '$lib/services/events.svelte';

	type Notification = components['schemas']['NotificationDTO'];

	let notifications: Array<Notification> = $state([]);
	let unreadCount = $state(0);
	let dropdownOpen = $state(false);
	const eventsClient = getEventsClient();

	async function loadNotifications() {
		try {
			const { data, error } = await client.GET('/notifications/', {
				params: { query: { limit: NOTIFICATION_PREVIEW_LIMIT } }
			});

			if (!error && data) {
				notifications = data.notifications;
				unreadCount = notifications.filter((n) => !n.seen_at).length;
			}
		} catch (e) {
			console.error('Failed to load notifications', e);
		}
	}

	async function markAllRead() {
		if (unreadCount === 0) return;
		try {
			const { error } = await client.POST('/notifications/mark-all-read');
			if (!error) {
				await loadNotifications();
			}
		} catch (e) {
			console.error('Failed to mark notifications as read', e);
		}
	}

	onMount(() => {
		void loadNotifications();

		if (!eventsClient) {
			return;
		}

		const handleUpdate = () => {
			void loadNotifications();
		};

		eventsClient.on('update_notifications', handleUpdate);

		return () => {
			eventsClient.off('update_notifications', handleUpdate);
		};
	});
</script>

<button
	id="notification-bell"
	aria-label="Открыть уведомления"
	aria-expanded={dropdownOpen}
	class="relative rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white focus-visible:outline-none dark:text-gray-400 dark:hover:bg-gray-700 dark:focus-visible:ring-gray-500 dark:focus-visible:ring-offset-gray-900"
>
	<BellSolid class="h-5 w-5" aria-hidden="true" />
	{#if unreadCount > 0}
		<div
			class="absolute top-1 right-1 inline-flex h-2.5 w-2.5 items-center justify-center rounded-full border-2 border-white bg-red-500 dark:border-gray-900"
			aria-hidden="true"
		></div>
	{/if}
</button>

<Dropdown
	triggeredBy="#notification-bell"
	bind:isOpen={dropdownOpen}
	class="w-full max-w-sm divide-y divide-gray-100 rounded-sm shadow-sm dark:divide-gray-700 dark:bg-gray-800"
>
	<div class="px-4 py-3">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<div class="text-left font-bold text-gray-900 dark:text-white">Последние уведомления</div>
				<div class="mt-1 text-left text-xs text-gray-500 dark:text-gray-400">
					Показаны 5 последних уведомлений
				</div>
			</div>
			<button
				type="button"
				class="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-primary-600 transition-colors hover:bg-primary-50 focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:text-primary-400 dark:hover:bg-gray-700"
				onclick={markAllRead}
				disabled={unreadCount === 0}
			>
				Прочитать все
			</button>
		</div>
	</div>
	<div class="max-h-96 overflow-y-auto">
		{#if notifications.length > 0}
			<div class="space-y-2 p-3">
				{#each notifications as notification (notification.id)}
					<NotificationListItem {notification} compact={true} />
				{/each}
			</div>
		{:else}
			<div class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
				Нет новых уведомлений
			</div>
		{/if}
	</div>

	<div class="p-2">
		<a
			href={resolve('/notifications')}
			class="block rounded-lg px-3 py-2 text-center text-sm font-medium text-primary-600 hover:bg-gray-100 dark:text-primary-400 dark:hover:bg-gray-700"
		>
			Все уведомления
		</a>
	</div>
</Dropdown>
