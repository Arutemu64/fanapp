<script lang="ts">
	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { uiHelpers } from 'flowbite-svelte';

	import type { LayoutProps } from './$types';

	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';
	import ConnectionBanner from './components/ConnectionBanner.svelte';

	let { data, children }: LayoutProps = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;

	// <main> is the scroll region and lives in this layout, so it persists across
	// navigation — SvelteKit's scroll handling only resets the window, never this
	// element. Drive it from the navigation callbacks, which fire on every
	// navigation while mounted: forward navigation starts a fresh page at the top,
	// and back/forward (popstate) restores where the user left the target page,
	// which the browser's own restoration can't do for a non-window scroller.
	// (A snapshot restores DOM state on back too, but only that half — it wouldn't
	// reset forward navigations — so one mechanism here is simpler.)
	// behavior:'instant' overrides the element's scroll-smooth, which would
	// otherwise animate the jump.
	let mainElement = $state<HTMLElement | null>(null);

	// Saved scroll offsets keyed by path+query. Plain storage, not reactive, and
	// held on the component rather than a module singleton so it stays scoped to
	// the app-shell session and is dropped on logout (the SPA state rule).
	const scrollPositions: Record<string, number> = {};

	function scrollKey(url: URL): string {
		return url.pathname + url.search;
	}

	beforeNavigate((navigation) => {
		if (navigation.from) {
			scrollPositions[scrollKey(navigation.from.url)] = mainElement?.scrollTop ?? 0;
		}
	});

	afterNavigate((navigation) => {
		if (!mainElement) return;

		if (navigation.type === 'popstate' && navigation.to) {
			const saved = scrollPositions[scrollKey(navigation.to.url)] ?? 0;
			mainElement.scrollTo({ top: saved, behavior: 'instant' });
			return;
		}

		mainElement.scrollTo({ top: 0, behavior: 'instant' });
	});
</script>

<div class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<SkipLink />

	<AppSidebar {user} {activeUrl} {isSidebarOpen} {closeSidebar} />

	<!-- <main> is the scrolling region, not this column: the landmark for the page's primary
		content must not also swallow the top bar and the connection banner. -->
	<div class="relative flex flex-1 flex-col overflow-hidden">
		<AppNavbar {user} toggleSidebar={sidebarUi.toggle} />

		<ConnectionBanner />

		<!-- Also the SkipLink target, which focuses it by id — hence tabindex="-1". -->
		<main
			bind:this={mainElement}
			id="main-content"
			tabindex="-1"
			class="relative flex-1 overflow-y-auto scroll-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
		>
			<ToastContainer />
			<!-- Bottom padding clears the fixed mobile bottom nav (h-16 + safe-area inset);
				md:p-6 resets it on desktop where the bottom nav is hidden. -->
			<div
				class="mx-auto max-w-5xl p-4 pb-[calc(6rem+env(safe-area-inset-bottom))] md:p-6 md:pt-4 lg:p-8 lg:pt-4"
			>
				{@render children()}
			</div>
		</main>
	</div>

	<AppBottomNav {activeUrl} />
</div>
