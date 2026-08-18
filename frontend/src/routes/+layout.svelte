<script lang="ts">
	import type { PWAInstallElement } from '@khmyznikov/pwa-install';

	import '../app.css';
	import type { ThemeConfig } from 'flowbite-svelte';

	import { navigating } from '$app/state';
	import UpdatePrompt from '$lib/components/UpdatePrompt.svelte';
	import { setEventsClient } from '$lib/services/events.svelte';
	import { setOfflineService } from '$lib/services/offline.svelte';
	import { setPwaService } from '$lib/services/pwa.svelte';
	import { setThemeService } from '$lib/services/theme.svelte';
	import { setToastService } from '$lib/services/toasts.svelte';
	import { registerServiceWorker } from '$lib/utils/serviceWorker';
	import * as Sentry from '@sentry/sveltekit';
	import { Spinner, ThemeProvider } from 'flowbite-svelte';
	import { onDestroy, onMount } from 'svelte';

	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();

	// Single source of truth for surfaces that otherwise drift: every one of these
	// classes used to be hand-copied onto each component instance (see git history
	// on this file) — one call site forgetting the override is how the drift
	// starts. Centralizing here means the Border-Radius Scale (docs/frontend.md §3)
	// is enforced by default instead of by convention. Components opt up/out via
	// their own class, which always wins through tailwind-merge.
	const flowbiteTheme: ThemeConfig = {
		// Flowbite's Card ships shadow-md + rounded-lg; this is the near-flat,
		// standard rounded-xl surface. Individual cards opt up to rounded-2xl
		// (large/feature/error) or shadow-sm (tappable) via their own class. The
		// focus-visible ring is inert on non-focusable <div> cards and gives every
		// href card (Flowbite renders an <a>) a visible keyboard focus indicator —
		// the one card a11y gap that was missing.
		card: {
			base: 'rounded-xl shadow-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:outline-none'
		},
		// Alert base already ships text-sm; only the radius (default rounded-lg)
		// needed lifting to the Inner tier every call site was independently doing.
		alert: 'rounded-xl',
		// Button ships rounded-lg; every primary/secondary/social button in the app
		// wants the Inner tier instead. Per-instance min-h-11 stays instance-side —
		// that's a touch-target decision (compact vs. full CTA), not a surface default.
		button: {
			base: 'rounded-xl'
		},
		// Popover menus (notification bell, avatar menu) are dropdown popovers per
		// the Inner tier; only one of the two call sites was applying it by hand.
		dropdown: 'rounded-xl',
		// Flowbite's Modal ships rounded-lg (Sub-group tier); modals are Outer tier.
		// header/footer need their own corner classes so they don't square off
		// against the now-rounder base.
		modal: {
			base: 'rounded-2xl',
			header: 'rounded-t-2xl',
			footer: 'rounded-b-2xl'
		}
	};

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

<ThemeProvider theme={flowbiteTheme}>
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
		icon="/icons/icon-512.png"
	></pwa-install>

	<!-- Prompts the user to reload when a new build has been cached by the SW. -->
	<UpdatePrompt />
</ThemeProvider>
