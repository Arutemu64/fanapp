<script lang="ts">
	import type { NotificationSeed } from '$lib/types/notifications';

	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { TAB_ROOTS } from '$lib/data/nav';
	import { setUnreadCountService } from '$lib/services/unreadCount.svelte';
	import { uiHelpers } from 'flowbite-svelte';

	import type { LayoutProps, Snapshot } from './$types';

	import NotificationsSkeleton from './(protected)/notifications/components/NotificationsSkeleton.svelte';
	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';
	import ConnectionBanner from './components/ConnectionBanner.svelte';
	import SectionSpinner from './components/SectionSpinner.svelte';
	import ScheduleSkeleton from './schedule/components/ScheduleSkeleton.svelte';
	import VotingSkeleton from './voting/components/VotingSkeleton.svelte';

	let { data, children }: LayoutProps = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	// Shared unread count for the bell badge and the notifications page. Seeded from
	// the streamed notification load once it resolves (first paint no longer waits on
	// it), and owned by the bell and page from there (SSE, mark-read, reconnect).
	// `seed()` applies only while the count is still provisional, so a fresher value
	// an SSE refresh may already have written — an authoritative zero included — wins.
	// `page.data` is loosely typed, so narrow the streamed promise back to its load type.
	const unread = setUnreadCountService();
	const notificationSeed = page.data.notifications as Promise<NotificationSeed | null>;
	void notificationSeed
		.then((seed) => {
			if (seed) unread.seed(seed.unreadCount);
		})
		.catch(() => {});

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;

	// <main> is the scroll region and lives in this layout, so it persists across
	// navigation — SvelteKit's scroll handling only manages the window, never this
	// element. Two mechanisms cover the two axes of return:
	//   - snapshot captures the container's offset per history entry and restores
	//     it on back/forward — the framework's tool for exactly this ("scroll
	//     positions on sidebars" in the docs), persisted to sessionStorage so it
	//     survives a reload.
	//   - scrollPositions remembers each primary tab's offset so re-entering a tab
	//     by a fresh tap (a push, which snapshots never restore) lands where you
	//     left it, the native bottom-tab-bar convention. Any other forward
	//     navigation — opening a detail page — resets to the top.
	// The two never fire on the same navigation: snapshot restores on popstate,
	// the tab restore on a push. behavior:'instant' overrides the element's
	// scroll-smooth, which would otherwise animate the jump.
	let mainElement = $state<HTMLElement | null>(null);

	// Per-tab scroll offsets keyed by pathname. A plain component-scoped object,
	// never a module singleton, so it is discarded when a logout unmounts this
	// layout rather than leaking into the next session.
	const scrollPositions: Record<string, number> = {};

	export const snapshot: Snapshot<number> = {
		capture: () => mainElement?.scrollTop ?? 0,
		restore: (top) => mainElement?.scrollTo({ top, behavior: 'instant' })
	};

	// Smooth (via the element's scroll-smooth, honoured because behavior is
	// omitted) so re-tapping the active tab eases to the top like a native tab bar.
	function scrollMainToTop() {
		mainElement?.scrollTo({ top: 0 });
	}

	beforeNavigate((navigation) => {
		const from = navigation.from?.url.pathname;
		if (from && TAB_ROOTS.has(from)) {
			scrollPositions[from] = mainElement?.scrollTop ?? 0;
		}
	});

	afterNavigate((navigation) => {
		// Back/forward is handled by snapshot.restore above.
		if (navigation.type === 'popstate') return;
		// A fresh push: restore a primary tab to where it was left, else reset.
		const to = navigation.to?.url.pathname ?? '';
		const top = TAB_ROOTS.has(to) ? (scrollPositions[to] ?? 0) : 0;
		mainElement?.scrollTo({ top, behavior: 'instant' });
	});

	// In-shell loading indicator. Section pages block on their `load`, so during a
	// switch the previous page stays painted until the new one commits; we replace
	// the content region with a skeleton (or a spinner) so feedback is local to
	// where the content will appear, the way a persistent app shell should behave.
	// Only real route changes populate `navigating` — an `invalidate()` data refresh
	// (e.g. the schedule's SSE reload) never does, so those never flash the loader.
	const LOADER_DELAY_MS = 250;

	// Gate on a short delay so fast navigations swap straight to the new page with
	// no placeholder flash; only a load that outlasts the delay reveals the loader.
	let showLoader = $state(false);
	$effect(() => {
		const target = navigating.to;
		// Scope to in-app section switches — auth navigations (login/logout) keep
		// their own form-level feedback and shouldn't paint a section loader.
		if (!target?.route?.id?.startsWith('/(app)')) {
			showLoader = false;
			return;
		}
		const timer = setTimeout(() => {
			showLoader = true;
		}, LOADER_DELAY_MS);
		return () => clearTimeout(timer);
	});

	// Sections with a regular, predictable layout get a bespoke skeleton keyed off
	// the destination route; everything else falls back to a centred spinner.
	let loaderRoute = $derived(navigating.to?.route?.id);
</script>

<div class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<SkipLink />

	<AppSidebar {user} {activeUrl} {isSidebarOpen} {closeSidebar} scrollToTop={scrollMainToTop} />

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
				{#if showLoader}
					{#if loaderRoute === '/(app)/schedule'}
						<ScheduleSkeleton />
					{:else if loaderRoute === '/(app)/voting'}
						<VotingSkeleton />
					{:else if loaderRoute === '/(app)/(protected)/notifications'}
						<NotificationsSkeleton />
					{:else}
						<SectionSpinner />
					{/if}
				{:else}
					{@render children()}
				{/if}
			</div>
		</main>
	</div>

	<AppBottomNav {activeUrl} scrollToTop={scrollMainToTop} />
</div>
