<script lang="ts">
	import type { NotificationDto } from '$lib/api/generated';

	import { resolve } from '$app/paths';
	import { markAllNotificationsRead, markNotificationsRead } from '$lib/api/generated';
	import {
		countUnreadNotificationsOptions,
		countUnreadNotificationsQueryKey,
		listUserNotificationsOptions,
		listUserNotificationsQueryKey
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import { offlineQueryOptions } from '$lib/api/queryClient';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { NOTIFICATION_BADGE_MAX, NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { setAppBadgeCount } from '$lib/utils/appBadge';
	import { Bell, Eye } from '@lucide/svelte';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	const queryClient = useQueryClient();

	const previewQuery = createQuery(() => ({
		...listUserNotificationsOptions({ query: { limit: NOTIFICATION_PREVIEW_LIMIT } }),
		...offlineQueryOptions,
		select: (data) => data.notifications
	}));
	let notifications: NotificationDto[] = $derived(previewQuery.data ?? []);

	// The badge is the true unread total, shared with the notifications page (which
	// clears it on open) — NOT the number of unread items in the capped preview,
	// which would pin the badge at 5 while dozens sit unread.
	//
	// There is deliberately no optimistic local delta: a delta and an authoritative
	// total cannot be ordered against each other without an "as-of" token the
	// endpoint doesn't return, so mixing them leaves the badge off by one. Every
	// change invalidates instead, and the badge converges within a round-trip. The
	// push toast already signals that a notification arrived.
	const unreadQuery = createQuery(() => ({
		...countUnreadNotificationsOptions(),
		...offlineQueryOptions,
		select: (data) => data.count
	}));
	let unreadCount = $derived(unreadQuery.data ?? 0);

	let badgeLabel = $derived(
		unreadCount > NOTIFICATION_BADGE_MAX ? `${NOTIFICATION_BADGE_MAX}+` : unreadCount
	);
	// Announce the count to screen readers so the unread state isn't conveyed by
	// the badge color alone.
	let bellLabel = $derived(
		unreadCount > 0 ? `Открыть уведомления, непрочитанных: ${unreadCount}` : 'Открыть уведомления'
	);
	const eventsClient = getEventsClient();
	const toastService = getToastService();

	// Every read-state change re-reads both: the list (items now marked seen) and the
	// true total, which the capped preview cannot derive — marking the visible five
	// read may still leave older unread items behind the badge. Invalidating both
	// keys covers every variant of each endpoint, including the notifications page's
	// own larger page size.
	function refreshNotifications(): Promise<unknown> {
		return Promise.all([
			queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() }),
			queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() })
		]);
	}

	// Mirror the unread count onto the installed app's icon (Badging API). This
	// also replaces the count-less "flag" badge the service worker sets on push
	// with the exact number once the app opens. The bell unmounts on every session
	// end — explicit logout AND a passive 401 expiry — so the icon badge is cleared
	// in the onMount teardown below, the one surface clearUserCache can't reach.
	$effect(() => {
		setAppBadgeCount(unreadCount);
	});

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
			const { error, response } = await markNotificationsRead({
				body: { notification_ids: unseenIds }
			});
			if (!error && response?.ok) {
				await refreshNotifications();
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	function handleNewNotification(notification: NotificationDto) {
		const alreadyInPreview = notifications.some(
			(existingNotification) => existingNotification.id === notification.id
		);
		if (alreadyInPreview) return;

		// Refetch rather than splicing the pushed item into the cached list: the
		// server decides both the preview's order and the unread total, and a local
		// insert would have to guess at both.
		void refreshNotifications();
		toastService.push(notification);
	}

	async function markAllRead() {
		if (unreadCount === 0) return;

		try {
			const { error, response } = await markAllNotificationsRead({});
			if (!error && response?.ok) {
				await refreshNotifications();
			}
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	function reloadAfterReconnect() {
		// Reload so notifications published while the stream was down aren't missed.
		void refreshNotifications();
	}

	onMount(() => {
		eventsClient.on('notification_created', handleNewNotification);
		// 'connection_established' fires on the first connect and on every reconnect.
		eventsClient.on('connection_established', reloadAfterReconnect);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			eventsClient.off('connection_established', reloadAfterReconnect);
			// Session ended (the bell only renders while logged in): drop the OS icon
			// badge so the previous user's count can't linger on a shared or installed
			// device. Covers passive 401 expiry too, which never runs AppNavbar's logout.
			setAppBadgeCount(0);
		};
	});

	// No `display` utility here: each trigger sets its own responsively. Baking
	// `inline-flex` in would collide with the desktop button's `hidden` at the same
	// specificity, and Tailwind emits `.inline-flex` after `.hidden`, so it would win
	// and leak the button onto mobile beside the `<a>` — a duplicate bell.
	const triggerClass =
		'relative h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:outline-none';
</script>

{#snippet bellContent()}
	<Bell class="h-5 w-5" aria-hidden="true" />
	{#if unreadCount > 0}
		<!-- Watermelon-primary badge per the design system (unseen dots are primary,
			not red — red reads as an error). The label is announced via aria-label. -->
		<span
			class="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-background bg-primary px-1 text-[10px] leading-none font-semibold text-primary-foreground"
			aria-hidden="true"
		>
			{badgeLabel}
		</span>
	{/if}
{/snippet}

<!-- On phones a cramped popover anchored to the corner is worse than the real
	screen, so the bell navigates straight to the full page. The dropdown preview
	is a desktop affordance where the extra viewport width makes it worthwhile. -->
<a
	href={resolve('/notifications')}
	aria-label={bellLabel}
	class="{triggerClass} inline-flex md:hidden"
>
	{@render bellContent()}
</a>

<DropdownMenu.Root
	onOpenChange={(open) => {
		if (open) void markVisibleRead();
	}}
>
	<DropdownMenu.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				id="notification-bell"
				aria-label={bellLabel}
				class="{triggerClass} hidden md:inline-flex"
			>
				{@render bellContent()}
			</button>
		{/snippet}
	</DropdownMenu.Trigger>
	<!-- sideOffset above the usual ~4 because the trigger is recessed inside the taller
		top bar: it must clear the bar's bottom padding, not just the bell button, or the
		menu tucks under the bar (which paints below it at a lower z-index). -->
	<DropdownMenu.Content align="end" sideOffset={16} class="w-80 max-w-sm p-0">
		<div class="flex items-center justify-between border-b border-border px-4 py-2">
			<div class="text-sm font-bold text-foreground">Уведомления</div>
			<button
				type="button"
				class="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
				onclick={markAllRead}
				disabled={unreadCount === 0}
			>
				Прочитать все
			</button>
		</div>

		<div class="max-h-96 divide-y divide-border overflow-y-auto">
			{#if notifications.length > 0}
				{#each notifications as notification (notification.id)}
					<NotificationListItem {notification} compact={true} />
				{/each}
			{:else}
				<div class="p-4 text-center text-sm text-muted-foreground">Уведомлений пока нет</div>
			{/if}
		</div>

		<a
			href={resolve('/notifications')}
			class="block border-t border-border bg-muted/50 py-2.5 text-center text-sm font-medium text-foreground hover:bg-muted"
		>
			<div class="inline-flex items-center">
				<Eye class="me-2 size-4 text-muted-foreground" />
				Все уведомления
			</div>
		</a>
	</DropdownMenu.Content>
</DropdownMenu.Root>
