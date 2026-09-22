<script lang="ts">
	import type { NotificationDto } from '$lib/api/generated';

	import { resolve } from '$app/paths';
	import {
		countUnreadNotificationsOptions,
		countUnreadNotificationsQueryKey,
		listUserNotificationsOptions,
		listUserNotificationsQueryKey,
		markAllNotificationsReadMutation,
		markNotificationsReadMutation
	} from '$lib/api/generated/@tanstack/svelte-query.gen';
	import NotificationListItem from '$lib/components/notifications/NotificationListItem.svelte';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { NOTIFICATION_BADGE_MAX, NOTIFICATION_PREVIEW_LIMIT } from '$lib/constants/notifications';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { setAppBadgeCount } from '$lib/utils/appBadge';
	import { Bell, Eye } from '@lucide/svelte';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	const queryClient = useQueryClient();
	const previewQuery = createQuery(() =>
		listUserNotificationsOptions({ query: { limit: NOTIFICATION_PREVIEW_LIMIT } })
	);
	// The badge is the true unread total, NOT the number of unread items in the
	// capped preview, which would pin the badge at 5 while dozens sit unread. It is
	// its own query so the notifications page, which clears it on open, invalidates
	// the same key and the two surfaces can never disagree.
	const unreadQuery = createQuery(() => countUnreadNotificationsOptions());

	let notifications = $derived(previewQuery.data?.notifications ?? []);
	let unreadCount = $derived(unreadQuery.data?.count ?? 0);

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

	const markRead = createMutation(() => markNotificationsReadMutation());
	const markAllRead = createMutation(() => markAllNotificationsReadMutation());

	// Mirror the unread count onto the installed app's icon (Badging API). This
	// also replaces the count-less "flag" badge the service worker sets on push
	// with the exact number once the app opens. The bell unmounts on every session
	// end — explicit logout AND a passive 401 expiry — so the icon badge is cleared
	// in the onMount teardown below, the one surface a cache reset can't reach.
	$effect(() => {
		setAppBadgeCount(unreadCount);
	});

	// Both surfaces change together on every read action, so they are always
	// invalidated as a pair: marking the visible five read may still leave older
	// unread items behind the badge, which only the count endpoint knows about.
	function refreshNotifications() {
		void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
		void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
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
			await markRead.mutateAsync({ body: { notification_ids: unseenIds } });
			refreshNotifications();
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	async function handleMarkAllRead() {
		if (unreadCount === 0) return;

		try {
			await markAllRead.mutateAsync({});
			// Zero the badge for instant feedback, then let the invalidation reconcile:
			// a notification committed between the server-side mark-all-read and this
			// line is still unread, and only the refetch surfaces it on the badge.
			queryClient.setQueryData(countUnreadNotificationsQueryKey(), { count: 0 });
			refreshNotifications();
		} catch (error) {
			console.error('Failed to mark notifications as read', error);
		}
	}

	function handleNewNotification(notification: NotificationDto) {
		const alreadyKnown = notifications.some((existing) => existing.id === notification.id);
		// Refetch rather than splicing the payload into the cache: the badge must be
		// the server's total, and a delta and an authoritative total can't be ordered
		// against each other without an "as-of" token the endpoint doesn't return.
		refreshNotifications();
		if (!alreadyKnown) toastService.push(notification);
	}

	onMount(() => {
		eventsClient.on('notification_created', handleNewNotification);
		// 'connection_established' fires on the first connect and on every reconnect;
		// refetch so notifications published while the stream was down aren't missed.
		eventsClient.on('connection_established', refreshNotifications);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			eventsClient.off('connection_established', refreshNotifications);
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
				onclick={handleMarkAllRead}
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
