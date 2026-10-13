<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';

	import * as Sentry from '@sentry/sveltekit';
	import { createQuery, QueryClientProvider } from '@tanstack/svelte-query';
	import { onDestroy, onMount } from 'svelte';

	import {
		countUnreadNotificationsQueryKey,
		getPublicConfigQueryKey,
		getScheduleQueryKey,
		getSyncSourcesQueryKey,
		getVotingStatusQueryKey,
		listScheduleChangesQueryKey,
		listUserNotificationsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { currentUserOptions, watchApiResponses } from '#lib/api/index.js';
	import Toaster from '#lib/components/ui/sonner/sonner.svelte';
	import UpdatePrompt from '#lib/components/UpdatePrompt.svelte';
	import { setEventsClient } from '#lib/services/events.svelte.js';
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
		isReachable
	});
	setToastService();
	const pwa = setPwaService();
	setThemeService();

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
			void navigator.storage?.persist().catch(() => {
				// Denied or unsupported: the cache stays best-effort.
			});
		}

		// Each teardown drops listeners, interceptors or a recovery poll, so dev HMR
		// re-creating this layout doesn't stack duplicates.
		const stopMonitor = startReachabilityMonitor();
		const stopWatching = watchApiResponses(queryClient, () => void session.expired());

		eventsClient.on('schedule_updated', handleScheduleUpdated);
		eventsClient.on('config_updated', handleConfigUpdated);
		eventsClient.on('notification_created', handleNotificationCreated);
		eventsClient.on('sync_run_updated', handleSyncRunUpdated);

		return () => {
			stopMonitor();
			stopWatching();
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

	function handleNotificationCreated() {
		void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
		void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
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
				id: String(user.data.id),
				username: user.data.username ?? undefined
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
	<title>ФАН ФАН</title>
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
	name="ФАН ФАН"
	icon="/icons/icon-512.png"
></pwa-install>

<!-- Prompts the user to reload when a new build has been cached by the SW. -->
<UpdatePrompt />
