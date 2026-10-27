<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import * as Sentry from '@sentry/sveltekit';

	import '../app.css';

	import { createQuery, focusManager, QueryClientProvider } from '@tanstack/svelte-query';
	import { onDestroy, onMount } from 'svelte';

	import type { NotificationDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		countUnreadNotificationsQueryKey,
		getPublicConfigQueryKey,
		getQuestQueryKey,
		getScheduleQueryKey,
		getVotingStatusQueryKey,
		listQuestHistoryQueryKey,
		listScheduleChangesQueryKey,
		listSyncSourcesQueryKey,
		listUserNotificationsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { watchApiResponses, watchBackgroundRefetchErrors } from '#lib/api/index.js';
	import { warmOfflineCache } from '#lib/api/offlineQueries.js';
	import { type QueuedWriteOutcome, watchQueuedWrites } from '#lib/api/writeQueue.js';
	import Toaster from '#lib/components/ui/sonner/sonner.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { trackPageView } from '#lib/services/analytics.js';
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

	beforeNavigate((navigation) => {
		if (!appUpdate.available) return;
		if (navigation.type !== 'link' || navigation.willUnload || !navigation.to) return;
		if (navigation.to.url.pathname === navigation.from?.url.pathname) return;
		navigation.cancel();
		appUpdate.apply(navigation.to.url.href);
	});

	afterNavigate(({ type, from, to }) => {
		if (type !== 'popstate' || !to) return;
		if (to.url.pathname === from?.url.pathname) return;
		trackPageView(to.url);
	});

	onMount(() => {
		document.getElementById('app-splash')?.remove();

		registerServiceWorker();

		if (pwa.isInstalled) {
			void (navigator.storage as StorageManager | undefined)?.persist().catch(() => {});
		}

		void flushPendingLogout();

		const stopMonitor = startReachabilityMonitor({
			onRecovered: () => {
				void flushPendingLogout();
				void warmOfflineCache(queryClient);
			}
		});
		const stopWatchingQueue = watchQueuedWrites(queryClient, reportQueuedWrite);
		void queryClient.resumePausedMutations();
		void warmOfflineCache(queryClient);
		const stopWarmingOnFocus = focusManager.subscribe((focused) => {
			if (focused) void warmOfflineCache(queryClient);
		});
		const stopUpdates = appUpdate.start();
		const stopWatching = watchApiResponses(queryClient, () => void session.expired());
		const stopWatchingRefetches = watchBackgroundRefetchErrors(queryClient, () =>
			toastService.add(m.refetch_failed(), 'error')
		);

		eventsClient.on('schedule_updated', handleScheduleUpdated);
		eventsClient.on('config_updated', handleConfigUpdated);
		eventsClient.on('notification_created', handleNotificationCreated);
		eventsClient.on('sync_run_updated', handleSyncRunUpdated);

		return () => {
			stopMonitor();
			stopWarmingOnFocus();
			stopWatchingQueue();
			stopUpdates();
			stopWatching();
			stopWatchingRefetches();
			eventsClient.off('schedule_updated', handleScheduleUpdated);
			eventsClient.off('config_updated', handleConfigUpdated);
			eventsClient.off('notification_created', handleNotificationCreated);
			eventsClient.off('sync_run_updated', handleSyncRunUpdated);
		};
	});

	const QUEUED_WRITE_COPY = {
		subscribe: { sent: m.subscribe_done, failed: m.subscribe_failed },
		unsubscribe: { sent: m.unsubscribe_done, failed: m.unsubscribe_failed },
		award: { sent: m.quest_tool_award_sent, failed: m.quest_tool_award_failed },
		feedback: { sent: m.feedback_sent, failed: m.feedback_send_failed }
	};

	function reportQueuedWrite(outcome: QueuedWriteOutcome) {
		const copy = QUEUED_WRITE_COPY[outcome.kind];
		if (outcome.ok) {
			toastService.add(copy.sent(), 'success');
			return;
		}
		const detail = getApiErrorDetail(outcome.error);
		const message = detail
			? m.queued_write_failed({ action: copy.failed(), detail })
			: copy.failed();
		toastService.add(message, 'error');
	}

	function handleScheduleUpdated() {
		void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
		void queryClient.invalidateQueries({ queryKey: listScheduleChangesQueryKey() });
	}

	function handleConfigUpdated() {
		void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
		void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
	}

	function handleNotificationCreated(notification: NotificationDto) {
		void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
		void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
		if (notification.type === 'quest') {
			void queryClient.invalidateQueries({ queryKey: getQuestQueryKey() });
			void queryClient.invalidateQueries({ queryKey: listQuestHistoryQueryKey() });
		}
	}

	function handleSyncRunUpdated() {
		void queryClient.invalidateQueries({ queryKey: listSyncSourcesQueryKey() });
	}

	const user = createQuery(
		() => currentUserOptions(),
		() => queryClient
	);

	let userId = $derived(user.data?.id ?? null);
	$effect(() => {
		if (userId !== null) void warmOfflineCache(queryClient);
	});

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
		eventsClient.destroy();
	});
</script>

<svelte:document ontouchstart={() => {}} />

<svelte:head>
	<title>{m.app_name()}</title>
</svelte:head>

<QueryClientProvider client={queryClient}>
	{@render children()}
</QueryClientProvider>

<Toaster />

<pwa-install
	{@attach (node: Element) => pwa.attach(node as PWAInstallElement)}
	manual-chrome
	manual-apple
	manifest-url="/manifest.json"
	name={m.app_name()}
	icon="/icons/icon-512.png"
></pwa-install>
