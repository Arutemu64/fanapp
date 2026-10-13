<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { Bell } from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import { countUnreadNotificationsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { NOTIFICATION_BADGE_MAX } from '#lib/constants/notifications.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { setAppBadgeCount } from '#lib/utils/appBadge.js';

	// The bell is a link to the notifications page on every screen size. A desktop
	// dropdown preview was dropped: the audience is almost always on a phone, and a
	// second list with its own read rules drifted from the page (its dots cleared
	// on open, it had its own mark-all), which is the bell/page mismatch that makes
	// users miss notifications.

	// The badge is the server's unread total, one query shared with the
	// notifications page (which clears it on open). It refetches on every
	// notification_created event and mark-read; there is deliberately no local
	// +1, since a delta can't be ordered against the authoritative total.
	const unreadQuery = createQuery(() => countUnreadNotificationsOptions());
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

	// Mirror the unread count onto the installed app's icon (Badging API). This
	// also replaces the count-less "flag" badge the service worker sets on push
	// with the exact number once the app opens. The bell unmounts on every session
	// end — explicit logout AND a passive 401 expiry — so the icon badge is cleared
	// in the onMount teardown below, the one surface the query cache can't reach.
	$effect(() => {
		setAppBadgeCount(unreadCount);
	});

	function handleNewNotification(notification: NotificationDto) {
		// On the notifications page the item already appears at the top of the
		// list, so a toast would only repeat it — Apple's HIG: in the foreground,
		// insert new data into the current view rather than notify:
		// https://developer.apple.com/design/human-interface-guidelines/notifications
		if (page.route.id === '/(app)/(protected)/notifications') return;
		toastService.push(notification);
	}

	onMount(() => {
		eventsClient.on('notification_created', handleNewNotification);

		return () => {
			eventsClient.off('notification_created', handleNewNotification);
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
	{#if unreadCount > 0}
		<!-- Watermelon-primary badge per the design system (unseen dots are primary,
			not red — red reads as an error). The label is announced via aria-label. -->
		<span
			class="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-background bg-primary px-1 text-3xs leading-none font-semibold text-primary-foreground"
			aria-hidden="true"
		>
			{badgeLabel}
		</span>
	{/if}
</a>
