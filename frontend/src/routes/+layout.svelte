<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';

	import { setApiClient } from '$lib/api/context';
	import { getScheduleOptions, getSubscriptionsOptions } from '$lib/api/queries';
	import Toaster from '$lib/components/ui/sonner/sonner.svelte';
	import UpdatePrompt from '$lib/components/UpdatePrompt.svelte';
	import { clearUserQueries, createQueryClient } from '$lib/query/client';
	import { bindOnlineManager } from '$lib/query/online';
	import { persisted } from '$lib/query/persist';
	import { createPersistOptions } from '$lib/query/persister';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setOfflineService } from '$lib/services/offline.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { dropRetiredCacheEntries } from '$lib/utils/offlineCache';
	import { registerServiceWorker } from '$lib/utils/serviceWorker';
	import * as Sentry from '@sentry/sveltekit';
	import { PersistQueryClientProvider } from '@tanstack/svelte-query-persist-client';
	import { onDestroy, onMount } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	// Owned by this component, never a module singleton: the cache holds per-user
	// data and a module-level client would outlive login/logout in this SPA.
	const queryClient = createQueryClient();
	// One client for every query, so they share interceptors and key against the
	// same baseUrl (see setApiClient).
	const apiClient = setApiClient();
	const persistOptions = createPersistOptions();
	// Pause and resume queries on *backend* reachability, not navigator.onLine.
	const unbindOnlineManager = bindOnlineManager();

	const eventsClient = setEventsClient();
	setToastService();
	const pwa = setPwaService();
	setThemeService();
	const offlineService = setOfflineService();

	// Seed the offline caches for pages the visitor may not open before losing
	// connectivity, so the schedule works offline from the first run. Runs once the
	// persister has finished restoring (whether or not it found a snapshot), so a
	// saved copy is never refetched on every launch; fire-and-forget, and a no-op
	// offline because the query pauses. Guests have no subscriptions to warm.
	function warmOfflineQueries() {
		const schedule = persisted(getScheduleOptions({ client: apiClient }), 'universal');
		if (queryClient.getQueryData(schedule.queryKey) === undefined) {
			void queryClient.prefetchQuery(schedule);
		}

		if (!data?.user) return;

		const subscriptions = persisted(getSubscriptionsOptions({ client: apiClient }), 'user');
		if (queryClient.getQueryData(subscriptions.queryKey) === undefined) {
			void queryClient.prefetchQuery(subscriptions);
		}
	}

	onMount(() => {
		// Remove the static boot splash (in app.html) now that the app has mounted.
		document.getElementById('app-splash')?.remove();

		// One-off cleanup of the entries the TanStack Query cache replaced.
		void dropRetiredCacheEntries();

		// SvelteKit's auto-registration is disabled (svelte.config.js) so we can
		// catch a rejected register() ourselves — see registerServiceWorker.
		registerServiceWorker();
	});

	$effect(() => {
		// Identity dropping to null is a logout or an expired session (the root load
		// decides which). Either way the previous account's cached queries must go,
		// so the next person on a shared device can't read them. The identity entry
		// itself is cleared by its own owners (handleLogout / the /me 401 branch).
		if (!data?.user) {
			clearUserQueries(queryClient);
		}
	});

	$effect(() => {
		if (data?.user) {
			Sentry.setUser({
				id: String(data.user.id),
				username: data.user.username ?? undefined
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
		// Same reason: drop the offline service's global listeners and its
		// recovery-poll timer so HMR doesn't stack duplicates.
		offlineService.destroy();
		unbindOnlineManager();
	});
</script>

<!-- Fallback title; pages override via their own <svelte:head><title>. -->
<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<PersistQueryClientProvider
	client={queryClient}
	{persistOptions}
	onSuccess={warmOfflineQueries}
	onError={warmOfflineQueries}
>
	{@render children()}
</PersistQueryClientProvider>

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
