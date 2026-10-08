<script lang="ts">
	import { afterNavigate, beforeNavigate, onNavigate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { navigating, page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';
	import { MediaQuery } from 'svelte/reactivity';

	import SkipLink from '#lib/components/SkipLink.svelte';
	import { TAB_ROOTS } from '#lib/data/nav.js';
	import { setUnreadCountService } from '#lib/services/unreadCount.svelte.js';

	import type { LayoutProps, Snapshot } from './$types';

	import NotificationsSkeleton from './(protected)/notifications/components/NotificationsSkeleton.svelte';
	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';
	import ConnectionBanner from './components/ConnectionBanner.svelte';
	import SectionSpinner from './components/SectionSpinner.svelte';
	import { navTransitionKind } from './navTransition';
	import ScheduleSkeleton from './schedule/components/ScheduleSkeleton.svelte';
	import VotingSkeleton from './voting/components/VotingSkeleton.svelte';

	let { data, children }: LayoutProps = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	// Shared unread count for the bell badge and the notifications page; the bell
	// loads it on mount and SSE, mark-read and reconnects keep it current.
	setUnreadCountService();

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
		// The applied offset, not the requested one: a page now too short for `top` clamps
		// it, and if that leaves scrollTop unchanged no `scroll` event would correct this.
		contentScrolled = (mainElement?.scrollTop ?? 0) > 0;
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
	// Whether content sits under the bar, which draws its bottom hairline only then. At
	// the top of a page the line would separate nothing; it is the scroll-edge behaviour
	// of the iOS navigation bar (transparent, no shadow, until content scrolls under it:
	// https://developer.apple.com/documentation/technotes/tn3106-customizing-uinavigationbar-appearance)
	// and of the Material 3 top app bar (`scrolledContainerColor`).
	let contentScrolled = $state(false);
	let navbarHeight = $state(0);
	let chromeHeight = $state(0);
	let lastScrollTop = 0;
	let scrollFrame = 0;

	// Hide-on-scroll is a mobile pattern: it reclaims scarce vertical space where a thumb
	// flick reads scroll intent cleanly. On desktop space is plentiful, the thin bar saves
	// almost nothing, and wheel/trackpad scrolling flip-flops direction enough to make the
	// slide flicker — so at md+ (the breakpoint that swaps the bottom nav for the sidebar)
	// the bar stays put. We keep tracking scroll everywhere and mask the result here, so
	// resizing across the breakpoint reveals the bar at once without a stale hidden state.
	const isDesktop = new MediaQuery('(min-width: 48rem)');
	let chromeHidden = $derived(navbarHidden && !isDesktop.current);

	// Reveal fast so the nav is back the instant you flick up; hide a touch slower so it
	// glides away rather than snapping. This asymmetry is the "headroom" feel.
	let chromeTransitionMs = $derived(chromeHidden ? 240 : 120);

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
			// Before the jitter guard: a slow drift back to 0 must still clear the hairline.
			contentScrolled = top > 0;
			const delta = top - lastScrollTop;
			if (Math.abs(delta) < SCROLL_DELTA_PX) return;
			// Reveal on any upward move; hide only while moving down past the bar's height.
			navbarHidden = delta > 0 && top > HIDE_NAVBAR_AFTER_PX;
			lastScrollTop = top;
		});
	}

	beforeNavigate((navigation) => {
		// SvelteKit runs navigation hooks for shallow routing too (the map viewer, the
		// login steps), but those only change page.state: there is no page to
		// restore scroll for or to animate into.
		if (navigation.shallow) return;
		const from = navigation.from?.url.pathname;
		if (from && TAB_ROOTS.has(from)) {
			scrollPositions[from] = mainElement?.scrollTop ?? 0;
		}
	});

	afterNavigate((navigation) => {
		if (navigation.shallow) return;
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

	// Native-style page transitions via the View Transitions API: a shared-axis slide
	// down or up the hierarchy, a fade-through between tabs (keyframes in app.css,
	// keyed off html[data-nav-transition]). Phones only — on desktop a slide reads as
	// lag rather than place, and a running transition swallows clicks for its duration,
	// so the md+ shell keeps its instant swap. Browsers without the API also keep it.
	// https://svelte.dev/blog/view-transitions
	// onNavigate runs once the destination's load has resolved, and `complete` settles
	// only after afterNavigate and the snapshot restore above have run, so the new
	// state is captured at its restored scroll offset.
	let transitionId = 0;

	onNavigate((navigation) => {
		if (navigation.shallow) return;
		if (!document.startViewTransition) return;
		if (isDesktop.current || prefersReducedMotion.current) return;
		if (navigation.willUnload || !navigation.from || !navigation.to) return;
		if (!navigation.to.route.id?.startsWith('/(app)')) return;

		let kind = navTransitionKind({
			from: navigation.from.url.pathname,
			to: navigation.to.url.pathname,
			fromBackHref: page.data.back && resolve(page.data.back.href),
			tabRoots: TAB_ROOTS
		});
		if (!kind) return;
		// A slow load has already swapped the section for its skeleton, so the content
		// arrives in place: sliding it in would move it away from where it is shown.
		if (showLoader) kind = 'fade';

		const id = ++transitionId;
		const root = document.documentElement;
		root.dataset.navTransition = kind;

		return new Promise<void>((resolve) => {
			const transition = document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
			// A transition is skipped when a newer navigation starts one of its own, and
			// its promises then reject. They are expected, so swallow them rather than let
			// them surface as unhandled rejections in Sentry.
			transition.ready.catch(() => {});
			transition.updateCallbackDone.catch(() => {});
			transition.finished
				.catch(() => {})
				.finally(() => {
					// Only the latest transition owns the attribute; an older, skipped one
					// settling late must not strip it from the one now running.
					if (id === transitionId) delete root.dataset.navTransition;
				});
		});
	});
</script>

<!-- Side safe-area padding keeps the shell out from under the notch and rounded
	corners of a landscape phone now that app.html opts into viewport-fit=cover; it
	resolves to 0 on a desktop or a portrait phone. -->
<div
	class="flex h-dvh w-full overflow-hidden bg-background pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)]"
>
	<SkipLink />

	<AppSidebar {activeUrl} scrollToTop={scrollMainToTop} />

	<!-- <main> is the scrolling region, not this column: the landmark for the page's primary
		content must not also swallow the top bar and the connection banner. -->
	<div class="relative flex flex-1 flex-col overflow-hidden">
		<!-- Top chrome overlays <main> instead of sharing its flex flow, so hiding the bar
			never resizes the scroll region (see the hide-on-scroll note above for why that
			loop is what made the bar blink). The column's overflow-hidden clips it as it
			slides to a negative `top`; sliding `top` rather than transforming keeps the bar's
			backdrop blur intact, and the connection banner below it rides up with it.
			The blur is on this wrapper, not the bar inside it: view-transition-name makes the
			wrapper a Backdrop Root, so a descendant's backdrop-filter would see only the
			wrapper's own (empty) backdrop and blur nothing
			(https://drafts.csswg.org/css-view-transitions-1/, "Rendering Consolidation").
			Under reduced transparency the wrapper turns opaque rather than just unblurred: the
			connection banner's tint is only /10, so without a solid fill behind it the page
			would show through the banner.
			transition-duration is set per state (fast reveal, slower hide). Dropdowns render
			in the native Popover top layer regardless of the wrapper. See handleMainScroll. -->
		<div
			bind:offsetHeight={chromeHeight}
			class="absolute inset-x-0 top-0 z-(--z-chrome) backdrop-blur-md transition-[top] ease-out [view-transition-name:top-chrome] motion-reduce:transition-none reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
			style:top={chromeHidden ? `-${navbarHeight}px` : '0px'}
			style:transition-duration={`${chromeTransitionMs}ms`}
		>
			<div bind:offsetHeight={navbarHeight}>
				<AppNavbar {user} {contentScrolled} />
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
			style:--sticky-top={chromeHidden ? `-${navbarHeight}px` : '0px'}
			style:--sticky-top-duration={`${chromeTransitionMs}ms`}
			class="relative flex flex-1 flex-col overflow-y-auto scroll-smooth [view-transition-name:page] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
		>
			<!-- Bottom padding lets the last row scroll 1rem clear of the floating mobile bottom nav;
				md:p-6 resets it on desktop where the bottom nav is hidden.
				grow (in <main>'s flex column) stretches this column to at least the visible height.
				<main>'s height is definite, so the grown height is too, and a page can fill it with
				min-h-full to pin trailing content (the profile footer) to the bottom on a short
				page (https://drafts.csswg.org/css-flexbox-1/#definite-sizes). w-full because a
				flex item with auto side margins would otherwise shrink to its content. -->
			<div
				class="mx-auto w-full max-w-5xl grow p-4 pb-[calc(var(--bottom-nav-clearance)+1rem)] md:p-6 md:pt-4 lg:p-8 lg:pt-4"
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
