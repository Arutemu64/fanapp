<script lang="ts">
	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { TAB_ROOTS } from '$lib/data/nav';
	import { setUnreadCountService } from '$lib/services/unreadCount.svelte';
	import { uiHelpers } from 'flowbite-svelte';
	import { untrack } from 'svelte';

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
	// Read this layout's own `data`, not `page.data`: the notifications page's load
	// returns a `notifications` array that clobbers the streamed promise in the merged
	// `page.data`, and `.then` on that array throws. `untrack` captures the seed promise
	// once at mount — the count is owned by SSE thereafter, so we don't re-seed on reload.
	const unread = setUnreadCountService();
	const notificationSeed = untrack(() => data.notifications);
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
		restore: (top) => restoreScroll(top)
	};

	// Programmatic scroll restore (snapshot back/forward, or a tab re-entry below).
	// A restore is not a user gesture, so it shows the bar and re-baselines the
	// hide-on-scroll tracker to the restored offset — otherwise the `scroll` event the
	// jump fires would read as a full-height downward scroll and hide the bar with no
	// input. snapshot.restore and afterNavigate can run in either order on popstate, so
	// both must leave the same baseline; this is the single place that guarantees it.
	function restoreScroll(top: number) {
		mainElement?.scrollTo({ top, behavior: 'instant' });
		navbarHidden = false;
		lastScrollTop = top;
	}

	// Smooth (via the element's scroll-smooth, honoured because behavior is
	// omitted) so re-tapping the active tab eases to the top like a native tab bar.
	function scrollMainToTop() {
		mainElement?.scrollTo({ top: 0 });
		revealNavbar();
	}

	// Hide-on-scroll for the top bar: hide it as the user scrolls down past the bar's
	// own height, reveal it on any scroll back up, so content gets the viewport while
	// the page title stays one flick away — the standard mobile "hidey bar". Reveal is
	// deliberately faster than hide (see chromeTransitionMs) so the nav snaps back the
	// instant you flick up. The bottom nav (primary navigation) stays put. We track
	// <main>, not the window, because <main> is the scroll region in this shell.
	//
	// The chrome overlays <main> (absolute, out of flow) rather than sharing its flex
	// column, and we slide it with `top`, never `transform`. Two constraints force this:
	//   - Out of flow so hiding the bar can't resize <main>. When the bar shared the flow
	//     and gave its space back on hide, the scroll region grew, which clamped scrollTop
	//     near the bottom and fired a spurious upward `scroll` event — reveal, regrow,
	//     re-hide: the resize/reveal loop that made the bar blink and stutter.
	//   - `top` on this wrapper, not `transform`: a transform on the wrapper (an ancestor
	//     of the blurred bar) re-roots the backdrop and kills the blur. Transforming the
	//     bar element alone would keep the blur, but it would leave the connection banner
	//     stranded below instead of sliding it up — and the moving bar must repaint its
	//     backdrop each frame regardless, so the compositor win a transform normally buys
	//     doesn't apply here anyway. Moving one out-of-flow wrapper via `top` costs a
	//     cheap layout of just that element; <main> never reflows.
	// `navbarHeight` (the bar alone) is how far we slide up on hide; `chromeHeight` (bar +
	// connection banner, bind:offsetHeight below) is <main>'s top padding so content clears
	// whatever chrome is showing.
	const HIDE_NAVBAR_AFTER_PX = 64; // never hide while the bar's own content is still on screen
	const SCROLL_DELTA_PX = 6; // ignore inertia/subpixel jitter that would flicker the bar
	let navbarHidden = $state(false);
	let navbarHeight = $state(0);
	let chromeHeight = $state(0);
	let lastScrollTop = 0;
	let scrollFrame = 0;

	// Reveal fast so the nav is back the instant you flick up; hide a touch slower so it
	// glides away rather than snapping. This asymmetry is the "headroom" feel.
	let chromeTransitionMs = $derived(navbarHidden ? 240 : 120);

	function revealNavbar() {
		navbarHidden = false;
		lastScrollTop = mainElement?.scrollTop ?? 0;
	}

	// Coalesce the scroll listener to one rAF per frame: many `scroll` events fire per
	// animation frame during momentum/inertial scrolling on mobile, so reading scrollTop
	// and flipping state once per frame — off the event — keeps the work off the critical
	// path and the scroll smooth. See https://developer.chrome.com/blog/inside-browser-part4.
	function handleMainScroll() {
		if (scrollFrame) return;
		scrollFrame = requestAnimationFrame(() => {
			scrollFrame = 0;
			const top = mainElement?.scrollTop ?? 0;
			const delta = top - lastScrollTop;
			if (Math.abs(delta) < SCROLL_DELTA_PX) return;
			// Reveal on any upward move; hide only while moving down past the bar's height.
			navbarHidden = delta > 0 && top > HIDE_NAVBAR_AFTER_PX;
			lastScrollTop = top;
		});
	}

	beforeNavigate((navigation) => {
		const from = navigation.from?.url.pathname;
		if (from && TAB_ROOTS.has(from)) {
			scrollPositions[from] = mainElement?.scrollTop ?? 0;
		}
	});

	afterNavigate((navigation) => {
		// Back/forward is handled by snapshot.restore above.
		if (navigation.type === 'popstate') {
			revealNavbar();
			return;
		}
		// A fresh push: restore a primary tab to where it was left, else reset.
		const to = navigation.to?.url.pathname ?? '';
		const top = TAB_ROOTS.has(to) ? (scrollPositions[to] ?? 0) : 0;
		restoreScroll(top);
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
		<!-- Top chrome overlays <main> instead of sharing its flex flow, so hiding the bar
			never resizes the scroll region (see the hide-on-scroll note above for why that
			loop is what made the bar blink). The column's overflow-hidden clips it as it
			slides to a negative `top`; sliding `top` rather than transforming keeps the bar's
			backdrop blur intact, and the connection banner below it rides up with it.
			transition-duration is set per state (fast reveal, slower hide). Dropdowns render
			in the native Popover top layer regardless of the wrapper. See handleMainScroll. -->
		<div
			bind:offsetHeight={chromeHeight}
			class="absolute inset-x-0 top-0 z-(--z-chrome) transition-[top] ease-out motion-reduce:transition-none"
			style:top={navbarHidden ? `-${navbarHeight}px` : '0px'}
			style:transition-duration={`${chromeTransitionMs}ms`}
		>
			<div bind:offsetHeight={navbarHeight}>
				<AppNavbar {user} toggleSidebar={sidebarUi.toggle} />
			</div>
			<ConnectionBanner />
		</div>

		<!-- Also the SkipLink target, which focuses it by id — hence tabindex="-1". padding-top
			clears the overlaid chrome; because the bar only hides once you've scrolled past it,
			that padding has already left the viewport by the time the bar is gone.

			--sticky-top is the top offset that in-flow sticky descendants (the schedule's block
			and nomination headers) must use instead of a bare top-0. A sticky element's offset is
			measured from the scroll container's padding edge, so top-0 would pin it at padding-top
			(chromeHeight) below the viewport — right under the chrome while it's shown, but a blank
			gap once the chrome has slid away. Shifting it up by navbarHeight when the bar is hidden
			cancels that: the header rests at the viewport top (or just below the connection banner,
			which stays), tracking the chrome's slide via the same duration. -->
		<main
			bind:this={mainElement}
			onscroll={handleMainScroll}
			id="main-content"
			tabindex="-1"
			style:padding-top={`${chromeHeight}px`}
			style:--sticky-top={navbarHidden ? `-${navbarHeight}px` : '0px'}
			style:--sticky-top-duration={`${chromeTransitionMs}ms`}
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
