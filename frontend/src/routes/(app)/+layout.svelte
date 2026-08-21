<script lang="ts">
	import { afterNavigate } from '$app/navigation';
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
	// element, leaving a new page scrolled to wherever the last one was. Reset it
	// on forward navigation; skip popstate so browser back/forward keeps its own
	// scroll behaviour. behavior:'instant' overrides the element's scroll-smooth,
	// which would otherwise animate the jump to top.
	let mainElement = $state<HTMLElement | null>(null);

	afterNavigate((navigation) => {
		if (navigation.type === 'popstate') return;
		mainElement?.scrollTo({ top: 0, behavior: 'instant' });
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
