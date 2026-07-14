<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';
	import { navigating } from '$app/state';
	import UpdatePrompt from '$lib/components/UpdatePrompt.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setOfflineService } from '$lib/services/offline.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import { setToastService } from '$lib/services/toasts.svelte';
	import * as Sentry from '@sentry/sveltekit';
	import { Spinner } from 'flowbite-svelte';
	import { onDestroy, onMount } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	const eventsClient = setEventsClient();
	setToastService();
	const pwa = setPwaService();
	setThemeService();
	setOfflineService();

	onMount(() => {
		// Remove the static boot splash (in app.html) now that the app has mounted.
		document.getElementById('app-splash')?.remove();
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
		eventsClient?.destroy();
	});
</script>

<!-- Fallback title; pages override via their own <svelte:head><title>. -->
<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

{@render children()}

<!--
	Navigation indicator. SPA route changes wait for the target `load` to resolve
	(e.g. fetching page data) before the new page paints; this floating spinner
	gives feedback during that gap. `pointer-events-none` keeps the UI usable.
-->
{#if navigating.to}
	<div
		class="pointer-events-none fixed inset-x-0 top-0 z-[100] flex justify-center pt-[calc(env(safe-area-inset-top)+0.75rem)]"
		role="status"
		aria-live="polite"
	>
		<span
			class="flex items-center gap-2 rounded-full bg-white/90 px-4 py-2 text-sm font-medium text-gray-700 shadow-lg backdrop-blur dark:bg-gray-800/90 dark:text-gray-200"
		>
			<Spinner size="5" color="primary" />
			Загрузка…
		</span>
	</div>
{/if}

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
	icon="/icons/icon-512x512.png"
></pwa-install>

<!-- Prompts the user to reload when a new build has been cached by the SW. -->
<UpdatePrompt />
