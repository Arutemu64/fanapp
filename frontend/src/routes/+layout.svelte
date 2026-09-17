<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';

	import Toaster from '$lib/components/ui/sonner/sonner.svelte';
	import UpdatePrompt from '$lib/components/UpdatePrompt.svelte';
	import { setCurrentUserContext } from '$lib/services/currentUser.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setOfflineService } from '$lib/services/offline.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { registerServiceWorker } from '$lib/utils/serviceWorker';
	import * as Sentry from '@sentry/sveltekit';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { onDestroy, onMount, untrack } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	// Identity read straight from the query cache, so a 401 elsewhere in the app —
	// or an explicit logout — updates every consumer without a route re-run. The
	// load already resolved it, so this never causes a second request.
	// Passed explicitly rather than read from context: QueryClientProvider sets that
	// context in its own component, which is below this script. `untrack` because
	// the cache is built once per boot — a load re-run hands back the same instance.
	const currentUser = setCurrentUserContext(untrack(() => data.queryClient));

	const eventsClient = setEventsClient();
	setToastService();
	const pwa = setPwaService();
	setThemeService();
	const offlineService = setOfflineService();

	onMount(() => {
		// Remove the static boot splash (in app.html) now that the app has mounted.
		document.getElementById('app-splash')?.remove();

		// SvelteKit's auto-registration is disabled (svelte.config.js) so we can
		// catch a rejected register() ourselves — see registerServiceWorker.
		registerServiceWorker();
	});

	$effect(() => {
		const user = currentUser.current;
		if (user) {
			Sentry.setUser({
				id: String(user.id),
				username: user.username ?? undefined
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

<QueryClientProvider client={data.queryClient}>
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
