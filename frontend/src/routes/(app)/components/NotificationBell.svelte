<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Bell from '@lucide/svelte/icons/bell';
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import { countUnreadNotificationsOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { NOTIFICATION_BADGE_MAX } from '#lib/constants/notifications.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getEventsClient } from '#lib/services/events.svelte.js';
	import { pushShowsOverOpenApp } from '#lib/services/pushDevice.svelte.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { setAppBadgeCount } from '#lib/utils/appBadge.js';

	const unreadQuery = createQuery(() => countUnreadNotificationsOptions());
	let unreadCount = $derived(unreadQuery.data?.count ?? 0);
	let badgeLabel = $derived(
		unreadCount > NOTIFICATION_BADGE_MAX ? `${NOTIFICATION_BADGE_MAX}+` : unreadCount
	);
	let bellLabel = $derived(
		unreadCount > 0 ? m.bell_label_unread({ count: unreadCount }) : m.bell_label()
	);
	const eventsClient = getEventsClient();
	const toastService = getToastService();

	$effect(() => {
		setAppBadgeCount(unreadCount);
	});

	let sessionEnded = false;

	function handleNewNotification(notification: NotificationDto) {
		if (page.route.id === '/(app)/(protected)/notifications') return;
		void pushShowsOverOpenApp().then((osShowsIt) => {
			if (!osShowsIt && !sessionEnded) {
				toastService.push(notification);
			}
		});
	}

	onMount(() => {
		eventsClient.on('notification_created', handleNewNotification);

		return () => {
			sessionEnded = true;
			eventsClient.off('notification_created', handleNewNotification);
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
		<span
			class="absolute top-0.5 right-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border-2 border-background bg-primary px-1 text-3xs leading-none font-semibold text-primary-foreground"
			aria-hidden="true"
		>
			{badgeLabel}
		</span>
	{/if}
</a>
