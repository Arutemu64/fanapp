<script lang="ts">
	import { client } from '$lib/api';
	import type { components } from '$lib/api/v1';
	import { Dropdown, DropdownGroup, DropdownItem, Avatar } from 'flowbite-svelte';
	import { BellSolid } from 'flowbite-svelte-icons';
	import { onMount, onDestroy } from 'svelte';
	import { getEventsClient } from '$lib/events.svelte';

	type Notification = components['schemas']['NotificationDTO'];

	let notifications: Array<Notification> = $state([]);
	let unreadCount = $state(0);
	const eventsClient = getEventsClient();

	async function loadNotifications() {
		try {
			const { data, error } = await client.GET('/notifications', {
				params: { query: { limit: 5 } }
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
		loadNotifications();
	});

	$effect(() => {
		if (!eventsClient) return;

		const handleUpdate = () => {
			loadNotifications();
		};

		eventsClient.on('update_notifications', handleUpdate);

		return () => {
			eventsClient.off('update_notifications', handleUpdate);
		};
	});
</script>

<button
	id="notification-bell"
	onclick={markAllRead}
	class="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus:ring-4 focus:ring-gray-200 focus:outline-hidden dark:text-gray-400 dark:hover:bg-gray-700 dark:focus:ring-gray-700"
>
	<BellSolid class="h-5 w-5" />
	{#if unreadCount > 0}
		<div
			class="absolute top-1 right-1 inline-flex h-2.5 w-2.5 items-center justify-center rounded-full border-2 border-white bg-red-500 dark:border-gray-900"
		></div>
	{/if}
</button>

<Dropdown
	triggeredBy="#notification-bell"
	class="w-full max-w-sm divide-y divide-gray-100 rounded-sm shadow-sm dark:divide-gray-700 dark:bg-gray-800"
>
	<div class="py-2 text-center font-bold text-gray-900 dark:text-white">Уведомления</div>
	<div class="max-h-96 overflow-y-auto">
		{#if notifications.length > 0}
			<DropdownGroup>
				{#each notifications as notification}
					<DropdownItem class="flex items-start space-x-4 p-3 rtl:space-x-reverse">
						<div class="flex w-full flex-col gap-1 ps-3 text-left">
							<div class="font-semibold whitespace-normal text-gray-900 dark:text-white">
								{notification.title}
							</div>
							<div class="text-sm whitespace-normal text-gray-500 dark:text-gray-400">
								{@html notification.body}
							</div>
							{#if notification.created_at}
								<div class="mt-1 text-xs text-primary-600 dark:text-primary-500">
									{new Date(notification.created_at).toLocaleString('ru')}
								</div>
							{/if}
						</div>
					</DropdownItem>
				{/each}
			</DropdownGroup>
		{:else}
			<div class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
				Нет новых уведомлений
			</div>
		{/if}
	</div>
</Dropdown>
