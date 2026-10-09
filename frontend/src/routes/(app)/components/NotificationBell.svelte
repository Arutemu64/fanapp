<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Bell } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import { NOTIFICATION_BADGE_MAX } from '#lib/constants/notifications.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { getUnreadCountService } from '#lib/services/unreadCount.svelte.js';
	import { setAppBadgeCount } from '#lib/utils/appBadge.js';
	import { onCatchUp } from '#lib/utils/reconnectRefresh.js';

	// The bell is a link to the notifications page on every screen size. A desktop
	// dropdown preview was dropped: the audience is almost always on a phone, and a
	// second list with its own read rules drifted from the page (its dots cleared
	// on open, it had its own mark-all), which is the bell/page mismatch that makes
	// users miss notifications.

	// The badge is the true unread total, shared with the notifications page (which
	// clears it on open).
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
	// with the exact number once the app opens. The bell unmounts on every session
	// end — explicit logout AND a passive 401 expiry — so the icon badge is cleared
	// in the onMount teardown below, the one surface clearUserCache can't reach.
	$effect(() => {
		setAppBadgeCount(unread.count);
	});

	function handleNewNotification(notification: NotificationDto) {
		// Reconcile the badge with the server rather than optimistically bumping it,
		// so the count can't drift out of sync with the true total (coalesced, so a
		// broadcast burst costs at most two round-trips).
		void unread.refresh();
		// On the notifications page the item already appears at the top of the
		// list, so a toast would only repeat it — Apple's HIG: in the foreground,
		// insert new data into the current view rather than notify:
		// https://developer.apple.com/design/human-interface-guidelines/notifications
		if (page.route.id === '/(app)/(protected)/notifications') return;
		toastService.push(notification);
	}

	function refreshAfterReconnect() {
		// Notifications published while the stream was down still count.
		void unread.refresh();
	}

	onMount(() => {
		// Load the count here rather than in a layout load: the bell renders as soon
		// as /me resolves, so it is just as early, and an explicit fetch doesn't hang
		// on SSE — the stream may already be connected before this mounts.
		void unread.refresh();

		eventsClient.on('notification_created', handleNewNotification);
		// The badge lives outside any page load, so the reconnect catch-up's
		// refreshAll() can't reach it — it subscribes to the catch-up instead.
		const stopCatchUp = onCatchUp(refreshAfterReconnect);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
			stopCatchUp();
			// Session ended (the bell only renders while logged in): drop the OS icon
			// badge so the previous user's count can't linger on a shared or installed
			// device. Covers passive 401 expiry too, which never runs LogoutButton.
			setAppBadgeCount(0);
		};
	});
</script>

<a
	href={resolve('notifications')}
	aria-label={bellLabel}
	class="relative inline-flex size-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:outline-none"
>
	<Bell class="size-5" aria-hidden="true" />
	{#if unread.count > 0}
		<!-- Watermelon-primary badge per the design system (unseen dots are primary,
			not red — red reads as an error). The label is announced via aria-label. -->
		<span
			class="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-background bg-primary px-1 text-[10px] leading-none font-semibold text-primary-foreground"
			aria-hidden="true"
		>
			{badgeLabel}
		</span>
	{/if}
</a>
