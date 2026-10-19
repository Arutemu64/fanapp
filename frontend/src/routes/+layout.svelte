<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import { beforeNavigate } from '$app/navigation';
	import * as Sentry from '@sentry/sveltekit';

	import '../app.css';

	import { createQuery, QueryClientProvider } from '@tanstack/svelte-query';
	import { onDestroy, onMount } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import {
		countUnreadNotificationsQueryKey,
		getPublicConfigQueryKey,
		getQuestQueryKey,
		getScheduleQueryKey,
		getSyncSourcesQueryKey,
		getVotingStatusQueryKey,
		listQuestHistoryQueryKey,
		listScheduleChangesQueryKey,
		listUserNotificationsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { watchApiResponses, watchBackgroundRefetchErrors } from '#lib/api/index.js';
	import Toaster from '#lib/components/ui/sonner/sonner.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { setAppUpdateService } from '#lib/services/appUpdate.svelte.js';
	import { setEventsClient } from '#lib/services/events.svelte.js';
	import { currentUserOptions, flushPendingLogout } from '#lib/services/identity.js';
	import { unsubscribeDevicePush } from '#lib/services/pushDevice.svelte.js';
	import { setPwaService } from '#lib/services/pwa.svelte.js';
	import { isReachable } from '#lib/services/reachability.js';
	import { startReachabilityMonitor } from '#lib/services/reachabilityMonitor.js';
	import { setSession } from '#lib/services/session.js';
	import { browserSessionRouter } from '#lib/services/sessionRouter.js';
	import { setThemeService } from '#lib/services/theme.svelte.js';
	import { setToastService } from '#lib/services/toasts.svelte.js';
	import { registerServiceWorker } from '#lib/utils/serviceWorker.js';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	// The root load runs once, so this is the same client for the whole session.
	// svelte-ignore state_referenced_locally
	const { queryClient } = data;

	const eventsClient = setEventsClient(queryClient);
	const session = setSession({
		queryClient,
		events: eventsClient,
		router: browserSessionRouter,
		isReachable,
		unsubscribePush: unsubscribeDevicePush
	});
	const toastService = setToastService();
	const pwa = setPwaService();
	setThemeService();
	const appUpdate = setAppUpdateService();

	// A waiting build is applied at the next page change rather than with a
	// prompt over the screen: a link tap is a natural break, and a full load there
	// costs nothing a client-side navigation would have kept. Only link taps to
	// another page — a goto() that rewrites a filter's query string, or a back
	// gesture (cancelling a popstate makes SvelteKit rewind history first), would
	// turn into a jarring reload.
	beforeNavigate((navigation) => {
		if (!appUpdate.available) return;
		if (navigation.type !== 'link' || navigation.willUnload || !navigation.to) return;
		if (navigation.to.url.pathname === navigation.from?.url.pathname) return;
		navigation.cancel();
		appUpdate.apply(navigation.to.url.href);
	});

	onMount(() => {
		// Remove the static boot splash (in app.html) now that the app has mounted.
		document.getElementById('app-splash')?.remove();

		// SvelteKit's auto-registration is disabled (svelte.config.js) so we can
		// catch a rejected register() ourselves — see registerServiceWorker.
		registerServiceWorker();

		// Exempt the saved offline screens from eviction under storage pressure, so a
		// full phone can't drop the programme before the festival. Only when
		// installed: Chrome and Safari grant or deny silently, an installed app
		// among WebKit's grounds for granting
		// (https://webkit.org/blog/14403/updates-to-storage-policy/), but Firefox
		// asks with a popup, which a passing visitor shouldn't get
		// (https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria).
		if (pwa.isInstalled) {
			void (navigator.storage as StorageManager | undefined)?.persist().catch(() => {
				// Denied or unsupported: the cache stays best-effort.
			});
		}

		// Revoke a session the user logged out of while offline. A boot that is
		// already online never crosses the recovery edge, so flush here too; offline
		// this is a no-op and the edge picks it up on reconnect. Until it clears, the
		// pending flag keeps the /me refetch on reconnect logged-out, so there's no
		// "logged back in" flicker in between.
		void flushPendingLogout();

		// Each teardown drops listeners, interceptors or a recovery poll, so dev HMR
		// re-creating this layout doesn't stack duplicates.
		const stopMonitor = startReachabilityMonitor({ onRecovered: () => void flushPendingLogout() });
		const stopUpdates = appUpdate.start();
		const stopWatching = watchApiResponses(queryClient, () => void session.expired());
		// Fixed copy, not the mapped code: the user didn't act, so «Билет не найден»
		// out of nowhere would read as a fault of theirs rather than a stale screen.
		const stopWatchingRefetches = watchBackgroundRefetchErrors(queryClient, () =>
			toastService.add(m.refetch_failed(), 'error')
		);

		eventsClient.on('schedule_updated', handleScheduleUpdated);
		eventsClient.on('config_updated', handleConfigUpdated);
		eventsClient.on('notification_created', handleNotificationCreated);
		eventsClient.on('sync_run_updated', handleSyncRunUpdated);

		return () => {
			stopMonitor();
			stopUpdates();
			stopWatching();
			stopWatchingRefetches();
			eventsClient.off('schedule_updated', handleScheduleUpdated);
			eventsClient.off('config_updated', handleConfigUpdated);
			eventsClient.off('notification_created', handleNotificationCreated);
			eventsClient.off('sync_run_updated', handleSyncRunUpdated);
		};
	});

	// SSE carries change signals only, so each event marks the queries it affects
	// stale: those on screen refetch at once, the rest when next shown. Keys match
	// by prefix, so a list key also covers its infinite (paginated) variant.

	// The change log has no event of its own: every change that adds a row to it
	// (create, undo) also broadcasts schedule_updated, a superset of the moments it
	// goes stale. The extra refetch that costs — a bulk import touches the schedule
	// but records no change row — is one request for the few staff watching it.
	function handleScheduleUpdated() {
		void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
		void queryClient.invalidateQueries({ queryKey: listScheduleChangesQueryKey() });
	}

	// The voting window is part of the festival config, so the voting status moves
	// with it.
	function handleConfigUpdated() {
		void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
		void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
	}

	function handleNotificationCreated(notification: NotificationDto) {
		void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
		void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
		// Every award and cancellation notifies the player, so the notification
		// doubles as the signal that their balance, rank and history moved.
		if (notification.type === 'quest') {
			void queryClient.invalidateQueries({ queryKey: getQuestQueryKey() });
			void queryClient.invalidateQueries({ queryKey: listQuestHistoryQueryKey() });
		}
	}

	// The payload only names the run; GET /sync/sources stays the source of truth.
	function handleSyncRunUpdated() {
		void queryClient.invalidateQueries({ queryKey: getSyncSourcesQueryKey() });
	}

	// Rendered above the provider, so the client is passed explicitly.
	const user = createQuery(
		() => currentUserOptions(),
		() => queryClient
	);

	$effect(() => {
		if (user.data) {
			Sentry.setUser({
				id: user.data.id,
				username: user.data.username
			});
		} else {
			Sentry.setUser(null);
		}
	});

	onDestroy(() => {
		// destroy() (not disconnect()) also unhooks the client's global
		// window/document listeners, so no zombie stream can resurrect —
		// matters mostly for dev HMR, which re-creates the layout.
		eventsClient.destroy();
	});
</script>

<!-- iOS Safari applies :active only while a touch listener sits on the element or an
	ancestor, so without this the press half of the `hover` variant (app.css) never
	shows on an iPhone.
	Empty and passive (Svelte's default for touchstart): it never delays scrolling.
	https://web.dev/articles/add-touch-to-your-site -->
<svelte:document ontouchstart={() => {}} />

<!-- Fallback title; pages override via their own <svelte:head><title>. -->
<svelte:head>
	<title>{m.app_name()}</title>
</svelte:head>

<QueryClientProvider client={queryClient}>
	{@render children()}
</QueryClientProvider>

<Toaster />

<!--
	Single instance of the install dialog. `manual-chrome`/`manual-apple` keep it
	hidden until we open it from our own buttons via PwaService.showInstallDialog().
	Locale (incl. Russian) is auto-detected by the library from the browser.
-->
<pwa-install
	{@attach (node: Element) => pwa.attach(node as PWAInstallElement)}
	manual-chrome
	manual-apple
	manifest-url="/manifest.json"
	name={m.app_name()}
	icon="/icons/icon-512.png"
></pwa-install>
