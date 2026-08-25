<script lang="ts">
	import type { NotificationDTO } from '$lib/types/notifications';

	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { createApiClient } from '$lib/api';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import { NOTIFICATION_BADGE_MAX, NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { getUnreadCountService } from '$lib/services/unreadCount.svelte';
	import { setAppBadgeCount } from '$lib/utils/appBadge';
	import { Dropdown, DropdownGroup } from 'flowbite-svelte';
	import { BellSolid, EyeSolid } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';

	const client = createApiClient();

	// Seed the preview from the layout-loaded data so the dropdown is correct on the
	// first paint. The SSE 'connection_established' handler refreshes it once the
	// stream is up. `page.data` is loosely typed (any), so narrow back to the load
	// type.
	const notificationPreview = page.data.notificationPreview as NotificationDTO[] | undefined;
	let notifications = $state<NotificationDTO[]>(notificationPreview ?? []);

	// The badge is the true unread total, shared with the notifications page (which
	// clears it on open) — NOT the number of unread items in the capped preview,
	// which would pin the badge at 5 while dozens sit unread.
	const unread = getUnreadCountService();
	let badgeLabel = $derived(
		unread.count > NOTIFICATION_BADGE_MAX ? `${NOTIFICATION_BADGE_MAX}+` : unread.count
	);
	// Announce the count to screen readers so the unread state isn't conveyed by
	// the badge color alone.
	let bellLabel = $derived(
		unread.count > 0 ? `Открыть уведомления, непрочитанных: ${unread.count}` : 'Открыть уведомления'
	);
	const eventsClient = getEventsClient();
	const toastService = getToastService();

	// Mirror the unread count onto the installed app's icon (Badging API). This
	// also replaces the count-less "flag" badge the service worker sets on push
	// with the exact number once the app opens; logout clears it (AppNavbar).
	$effect(() => {
		setAppBadgeCount(unread.count);
	});

	async function loadNotifications() {
		try {
			const { data, error, response } = await client.GET('/notifications/', {
				params: { query: { limit: NOTIFICATION_PREVIEW_LIMIT } }
			});

			if (!error && response.ok && data) {
				notifications = data.notifications;
			}
		} catch (error) {
			console.error('Failed to load notifications', error);
		}
	}

	// Clicking the bell to open the dropdown counts as seeing the previewed items
	// (mark-on-open), so clear their unread state server-side and reconcile the
	// badge with the total. Idempotent: a click that closes the dropdown finds
	// nothing unseen and no-ops.
	async function markVisibleRead() {
		const unseenIds = notifications
			.filter((notification) => !notification.seen_at)
			.map((notification) => notification.id);
		if (unseenIds.length === 0) return;

		try {
			const { error, response } = await client.POST('/notifications/mark-read', {
				body: { notification_ids: unseenIds }
			});
			if (!error && response.ok) {
				// Reload the preview (items now read) and the true total — marking the
				// visible five read may still leave older unread items behind the badge.
				await Promise.all([loadNotifications(), unread.refresh()]);
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	function addNotificationToPreview(notification: NotificationDTO) {
		const alreadyExists = notifications.some(
			(existingNotification) => existingNotification.id === notification.id
		);

		notifications = [
			notification,
			...notifications.filter((existingNotification) => existingNotification.id !== notification.id)
		].slice(0, NOTIFICATION_PREVIEW_LIMIT);

		return !alreadyExists;
	}

	function handleNewNotification(notification: NotificationDTO) {
		const isNewNotification = addNotificationToPreview(notification);
		if (isNewNotification) {
			// Reconcile the badge with the server rather than optimistically bumping it,
			// so the count can't drift out of sync with the true total (coalesced, so a
			// broadcast burst costs at most two round-trips).
			void unread.refresh();
			toastService.push(notification);
		}
	}

	async function markAllRead() {
		if (unread.count === 0) return;

		try {
			const { error, response } = await client.POST('/notifications/mark-all-read');
			if (!error && response.ok) {
				unread.clear();
				await loadNotifications();
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	function reloadAfterReconnect() {
		// Reload so notifications published while the stream was down aren't missed.
		void loadNotifications();
		void unread.refresh();
	}

	onMount(() => {
		eventsClient.on('notification_created', handleNewNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', reloadAfterReconnect);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			eventsClient.off('connection_established', reloadAfterReconnect);
		};
	});

	const triggerClass =
		'relative inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 focus-visible:ring-offset-white focus-visible:outline-none dark:text-gray-400 dark:hover:bg-gray-700 dark:focus-visible:ring-gray-500 dark:focus-visible:ring-offset-gray-900';
</script>

{#snippet bellContent()}
	<BellSolid class="h-5 w-5" aria-hidden="true" />
	{#if unread.count > 0}
		<!-- Watermelon-primary badge per the design system (unseen dots are primary,
			not red — red reads as an error). The label is announced via aria-label. -->
		<span
			class="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-white bg-primary-600 px-1 text-[10px] leading-none font-semibold text-white dark:border-gray-900 dark:bg-primary-500"
			aria-hidden="true"
		>
			{badgeLabel}
		</span>
	{/if}
{/snippet}

<!-- On phones a cramped popover anchored to the corner is worse than the real
	screen, so the bell navigates straight to the full page. The dropdown preview
	is a desktop affordance where the extra viewport width makes it worthwhile. -->
<a href={resolve('/notifications')} aria-label={bellLabel} class="{triggerClass} md:hidden">
	{@render bellContent()}
</a>

<button
	id="notification-bell"
	aria-label={bellLabel}
	onclick={markVisibleRead}
	class="{triggerClass} hidden md:inline-flex"
>
	{@render bellContent()}
</button>

<Dropdown
	triggeredBy="#notification-bell"
	class="w-full max-w-sm divide-y divide-gray-100 dark:divide-gray-700 dark:bg-gray-800"
>
	<div class="flex items-center justify-between px-4 py-2">
		<div class="text-center font-bold text-gray-900 dark:text-white">Уведомления</div>
		<button
			type="button"
			class="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-primary-600 transition-colors hover:bg-primary-50 focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 dark:text-primary-400 dark:hover:bg-gray-700"
			onclick={markAllRead}
			disabled={unread.count === 0}
		>
			Прочитать все
		</button>
	</div>

	<div class="max-h-96 overflow-y-auto">
		{#if notifications.length > 0}
			<DropdownGroup>
				{#each notifications as notification (notification.id)}
					<NotificationListItem {notification} compact={true} />
				{/each}
			</DropdownGroup>
		{:else}
			<div class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
				Уведомлений пока нет
			</div>
		{/if}
	</div>

	<a
		href={resolve('/notifications')}
		class="-my-1 block bg-gray-50 py-2 text-center text-sm font-medium text-gray-900 hover:bg-gray-100 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
	>
		<div class="inline-flex items-center">
			<EyeSolid class="me-2 h-4 w-4 text-gray-500 dark:text-gray-400" />
			Все уведомления
		</div>
	</a>
</Dropdown>
