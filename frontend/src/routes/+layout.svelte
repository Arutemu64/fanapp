<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';

	import { idbPersister } from '$lib/api/persister';
	import { PERSISTED_GC_TIME_MS } from '$lib/api/queryClient';
	import Toaster from '$lib/components/ui/sonner/sonner.svelte';
	import UpdatePrompt from '$lib/components/UpdatePrompt.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setOfflineService } from '$lib/services/offline.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { registerServiceWorker } from '$lib/utils/serviceWorker';
	import * as Sentry from '@sentry/sveltekit';
	import { PersistQueryClientProvider } from '@tanstack/svelte-query-persist-client';
	import { onDestroy, onMount, untrack } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	// One QueryClient per app boot, created in this layout's `load` and never
	// replaced — untrack says so, since reading it here would otherwise look like a
	// missed reactive dependency.
	const queryClient = untrack(() => data.queryClient);

	const eventsClient = setEventsClient(queryClient);
	setToastService();
	const pwa = setPwaService();
	setThemeService();
	const offlineService = setOfflineService(queryClient);

	onMount(() => {
		// Remove the static boot splash (in app.html) now that the app has mounted.
		document.getElementById('app-splash')?.remove();

		// SvelteKit's auto-registration is disabled (svelte.config.js) so we can
		// catch a rejected register() ourselves — see registerServiceWorker.
		registerServiceWorker();
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
	});
</script>

<!-- Fallback title; pages override via their own <svelte:head><title>. -->
<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

<!--
	Restores the dehydrated cache from IndexedDB before rendering, so an offline
	boot paints from the last synced data instead of empty states. `maxAge` must
	not outlive the client's `gcTime`, or a restored query would be evicted before
	anything could read it.
-->
<PersistQueryClientProvider
	client={queryClient}
	persistOptions={{ maxAge: PERSISTED_GC_TIME_MS, persister: idbPersister }}
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
