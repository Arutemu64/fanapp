<script lang="ts">
	import { afterNavigate, beforeNavigate, onNavigate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { createQuery } from '@tanstack/svelte-query';
	import { prefersReducedMotion } from 'svelte/motion';
	import { MediaQuery } from 'svelte/reactivity';

	import { currentUserOptions } from '#lib/api/index.js';
	import SkipLink from '#lib/components/SkipLink.svelte';
	import { TAB_ROOTS } from '#lib/data/nav.js';

	import type { LayoutProps } from './$types';

	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';
	import ConnectionBanner from './components/ConnectionBanner.svelte';
	import { navTransitionKind } from './navTransition';

	let { children }: LayoutProps = $props();

	let activeUrl = $derived(page.url.pathname);
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);

	// The document is the scroll region, so SvelteKit's own scroll handling restores the
	// offset on back/forward (and across a reload) and resets it on a fresh push. The one
	// thing it doesn't do is the native bottom-tab-bar convention: re-entering a primary
	// tab by a fresh tap lands where you left it. scrollPositions remembers each tab's
	// offset for that, and afterNavigate below applies it on top of SvelteKit's reset.
	// A plain component-scoped object, never a module singleton, so it is discarded when a
	// logout unmounts this layout rather than leaking into the next session.
	const scrollPositions: Record<string, number> = {};

	// Not the CSS scroll-behavior on <html>: SvelteKit's navigation scroll reset would
	// animate with it.
	let scrollBehavior: ScrollBehavior = $derived(
		prefersReducedMotion.current ? 'instant' : 'smooth'
	);

	// Re-tapping the active tab eases to the top, like a native tab bar.
	function scrollPageToTop() {
		window.scrollTo({ top: 0, behavior: scrollBehavior });
		revealNavbar();
	}

	// Hide-on-scroll for the top bar: hide it as the user scrolls down past the bar's
	// own height, reveal it on any scroll back up, so content gets the viewport while
	// the page title stays one flick away — the standard mobile "hidey bar". Reveal is
	// deliberately faster than hide (see chromeTransitionMs) so the nav snaps back the
	// instant you flick up. The bottom nav (primary navigation) stays put.
	//
	// The chrome is sticky, and we slide it with `top`, never `transform`:
	//   - Sticky keeps its place in the flow whether shown or hidden, so hiding the bar
	//     never changes the document's height. A bar that gave its space back on hide
	//     would shift the content, which fires a spurious upward `scroll` event — reveal,
	//     regrow, re-hide: a resize/reveal loop that makes the bar blink and stutter.
	//   - `top` on this wrapper, not `transform`: a transform on the wrapper (an ancestor
	//     of the blurred bar) re-roots the backdrop and kills the blur. Transforming the
	//     bar element alone would keep the blur, but it would leave the connection banner
	//     stranded below instead of sliding it up — and the moving bar must repaint its
	//     backdrop each frame regardless, so the compositor win a transform normally buys
	//     doesn't apply here anyway.
	// `navbarHeight` (the bar alone) is how far we slide up on hide; `chromeHeight` (bar +
	// connection banner) sets where the page's own sticky headers rest beneath it.
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

	// Where the page's sticky headers rest: just under whatever chrome is showing.
	let stickyTop = $derived(chromeHidden ? chromeHeight - navbarHeight : chromeHeight);

	// Keyboard focus, find-in-page and anchor jumps scroll their target into view; the
	// scroll padding keeps it clear of the sticky chrome and the floating bottom nav,
	// which would otherwise cover it (WCAG 2.4.11 Focus Not Obscured, technique C43:
	// https://www.w3.org/WAI/WCAG22/Techniques/css/C43). Set on <html> because the
	// document is the scroll container, and removed with the shell that needs it.
	// The full chrome height even while the bar is hidden: a jump up to a target reads
	// as an upward scroll and brings the bar back over it.
	$effect(() => {
		const root = document.documentElement;
		root.style.scrollPaddingTop = `${chromeHeight}px`;
		root.style.scrollPaddingBottom = isDesktop.current
			? ''
			: 'calc(var(--bottom-nav-clearance) + var(--bottom-accessory-clearance))';
		return () => {
			root.style.removeProperty('scroll-padding-top');
			root.style.removeProperty('scroll-padding-bottom');
		};
	});

	function revealNavbar() {
		navbarHidden = false;
		lastScrollTop = window.scrollY;
	}

	// A programmatic scroll (SvelteKit's restore or reset, a tab re-entry) is not a user
	// gesture, so it shows the bar and re-baselines the hide-on-scroll tracker to the new
	// offset — otherwise the `scroll` event the jump fires would read as a full-height
	// downward scroll and hide the bar with no input.
	function syncChromeToScroll() {
		revealNavbar();
		contentScrolled = window.scrollY > 0;
	}

	// Coalesce the scroll listener to one rAF per frame: many `scroll` events fire per
	// animation frame during momentum/inertial scrolling on mobile, so reading scrollY
	// and flipping state once per frame — off the event — keeps the work off the critical
	// path and the scroll smooth. See https://developer.chrome.com/blog/inside-browser-part4.
	function handleScroll() {
		if (scrollFrame) return;
		scrollFrame = requestAnimationFrame(() => {
			scrollFrame = 0;
			const top = window.scrollY;
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
			scrollPositions[from] = window.scrollY;
		}
	});

	// Runs after SvelteKit has restored (back/forward) or reset (push) the scroll.
	afterNavigate((navigation) => {
		if (navigation.shallow) return;
		const to = navigation.to?.url.pathname ?? '';
		const savedTop = scrollPositions[to];
		if (
			navigation.type !== 'popstate' &&
			TAB_ROOTS.has(to) &&
			savedTop !== undefined &&
			savedTop > 0
		) {
			window.scrollTo({ top: savedTop, behavior: 'instant' });
		}
		syncChromeToScroll();
	});

	// Native-style page transitions via the View Transitions API: a shared-axis slide
	// down or up the hierarchy, a fade-through between tabs (keyframes in app.css,
	// keyed off html[data-nav-transition]). Phones only — on desktop a slide reads as
	// lag rather than place, and a running transition swallows clicks for its duration,
	// so the md+ shell keeps its instant swap. Browsers without the API also keep it.
	// https://svelte.dev/blog/view-transitions
	// onNavigate runs once the destination's load has resolved, and `complete` settles
	// only after SvelteKit's scroll handling and afterNavigate above have run, so the new
	// state is captured at its restored scroll offset. The page itself animates as the
	// default `root` snapshot, which is viewport-sized; the bars carry their own names so
	// they hold still.
	let transitionId = 0;

	onNavigate((navigation) => {
		if (navigation.shallow) return;
		if (!('startViewTransition' in document)) return;
		if (isDesktop.current || prefersReducedMotion.current) return;
		if (!navigation.from || !navigation.to) return;
		if (!navigation.to.route.id?.startsWith('/(app)')) return;

		const kind = navTransitionKind({
			from: navigation.from.url.pathname,
			to: navigation.to.url.pathname,
			fromBackHref: page.data.back && resolve(page.data.back.href),
			tabRoots: TAB_ROOTS
		});
		if (!kind) return;

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

<svelte:window onscroll={handleScroll} />

<!-- Side safe-area padding keeps the shell out from under the notch and rounded
	corners of a landscape phone now that app.html opts into viewport-fit=cover; it
	resolves to 0 on a desktop or a portrait phone. -->
<div
	class="flex min-h-dvh w-full bg-background pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)]"
>
	<SkipLink />

	<AppSidebar {activeUrl} scrollToTop={scrollPageToTop} />

	<!-- overflow-x-clip, not overflow-hidden: clip guards against a wide child scrolling the
		page sideways without making this column a scroll container, which would break every
		sticky element inside it (the chrome, the schedule's headers). -->
	<div class="relative flex min-w-0 flex-1 flex-col overflow-x-clip">
		<!-- Top chrome: the bar and the connection banner, sliding together (see the
			hide-on-scroll note above). transition-duration is set per state (fast reveal,
			slower hide).
			The blur is on this wrapper, not the bar inside it: view-transition-name makes the
			wrapper a Backdrop Root, so a descendant's backdrop-filter would see only the
			wrapper's own (empty) backdrop and blur nothing
			(https://drafts.csswg.org/css-view-transitions-1/, "Rendering Consolidation").
			Under reduced transparency the wrapper turns opaque rather than just unblurred: the
			connection banner's tint is only /10, so without a solid fill behind it the page
			would show through the banner.
			Dropdowns render in the native Popover top layer regardless of the wrapper. -->
		<div
			bind:offsetHeight={chromeHeight}
			class="sticky z-(--z-chrome) backdrop-blur-md transition-[top] ease-out [view-transition-name:top-chrome] motion-reduce:transition-none reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
			style:top={chromeHidden ? `-${navbarHeight}px` : '0px'}
			style:transition-duration={`${chromeTransitionMs}ms`}
		>
			<div bind:offsetHeight={navbarHeight}>
				<AppNavbar {user} {contentScrolled} />
			</div>
			<ConnectionBanner />
		</div>

		<!-- Also the SkipLink target, which focuses it by id — hence tabindex="-1".

			--sticky-top is the top offset that sticky descendants (the schedule's block and
			nomination headers) must use instead of a bare top-0, which would tuck them under
			the chrome. It tracks the chrome's slide via the same duration, so a header rests
			at the viewport top (or just below the connection banner, which stays) once the
			bar has slid away. -->
		<main
			id="main-content"
			tabindex="-1"
			style:--sticky-top={`${stickyTop}px`}
			style:--sticky-top-duration={`${chromeTransitionMs}ms`}
			class="flex flex-1 flex-col focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
		>
			<!-- Bottom padding lets the last row scroll 1rem clear of the floating mobile bottom nav;
				md:p-6 resets it on desktop where the bottom nav is hidden.
				grow (in <main>'s flex column) stretches this column to at least the visible
				height. A page that pins trailing content to the bottom on a short page (the
				profile footer) marks its root data-fill-column, and this column turns into a
				flex column so that root can grow into the space: a percentage min-height has
				nothing definite to resolve against here. Opt-in rather than always flex, since
				a flex item with auto side margins shrinks to its content. w-full for the same
				reason. -->
			<div
				class="mx-auto w-full max-w-5xl grow p-4 pb-[calc(var(--bottom-nav-clearance)+1rem)] has-[>[data-fill-column]]:flex has-[>[data-fill-column]]:flex-col md:p-6 md:pt-4 lg:p-8 lg:pt-4"
			>
				{@render children()}
			</div>
		</main>
	</div>

	<AppBottomNav {activeUrl} scrollToTop={scrollPageToTop} />
</div>
