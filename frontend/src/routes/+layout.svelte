<script lang="ts">
	import type { LayoutProps } from './$types';
	import '../app.css';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';
	import { onDestroy } from 'svelte';
	import * as Sentry from '@sentry/sveltekit';

	let { children, data }: LayoutProps = $props();

	const eventsClient = setEventsClient();
	setToastService();
	const pwa = setPwaService();
	setThemeService();

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
		eventsClient?.disconnect();
	});
</script>

<!-- Fallback title; pages override via their own <svelte:head><title>. -->
<svelte:head>
	<title>ФАН ФАН</title>
</svelte:head>

{@render children()}

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
