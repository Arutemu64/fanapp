<script lang="ts">
	import { resolve } from '$app/paths';

	import { PRIMARY_NAV_ITEMS } from '#lib/data/nav.js';
	import { isNavItemActive } from '#lib/utils/nav.js';

	interface Props {
		activeUrl: string;
		scrollToTop: () => void;
	}

	let { activeUrl, scrollToTop }: Props = $props();

	// -1 on a page no tab claims (e.g. notifications): the capsule fades out in place.
	let activeIndex = $derived(
		PRIMARY_NAV_ITEMS.findIndex((item) => isNavItemActive(activeUrl, item))
	);
	let indicatorShift = $derived(`${Math.max(activeIndex, 0) * 100}% 0`);
</script>

<!-- A floating glass pill, the iOS 26 tab bar shape: it "floats above the content"
     (https://developer.apple.com/videos/play/wwdc2025/284/), so content stays visible
     around and through it instead of stopping at an opaque band. Its geometry lives in
     app.css (--bottom-nav-gap / --bottom-nav-clearance) because every surface that
     floats above it offsets from the same edge.
     The full-width <nav> only positions the pill; pointer-events-none lets a tap beside
     the pill reach the content underneath. No side safe-area padding: the pill is capped
     at max-w-md and centred, so on a landscape phone it never reaches the notch.
     Blur is 16px: a persistent blurred layer re-composites its backdrop on every scroll
     frame, and 8–16px is the budget for one on mid-range phones
     (https://www.buildmvpfast.com/blog/liquid-glass-css-backdrop-filter-recipes-2026).
     The tint is /85, not the airier /70: over the schedule's dense rows, /70 let a row's
     bold title read through the tab labels. Refracting "liquid glass" (an SVG
     displacement backdrop-filter, Chromium-only) was tried and rejected for the same
     reason, worse: it keeps the centre of the glass sharp, right where the labels sit.
     The view-transition-name sits on the pill, not the <nav>: a named element is a
     Backdrop Root, so naming the wrapper would leave the pill nothing to blur
     (https://drafts.csswg.org/css-view-transitions-1/, "Rendering Consolidation").
     preload-code="viewport" fetches every tab's code as soon as the bar renders, so a
     first tap on a tab never waits on a chunk; data still waits for the tap
     (preload-data="hover" on <body> fires on touchstart). -->
<nav
	aria-label="Разделы"
	data-sveltekit-preload-code="viewport"
	class="pointer-events-none fixed inset-x-0 bottom-(--bottom-nav-gap) z-(--z-overlay) px-2 select-none [-webkit-touch-callout:none] min-[25rem]:px-3 md:hidden"
>
	<div
		class="pointer-events-auto relative mx-auto grid h-16 max-w-md grid-cols-5 rounded-full border border-border/60 bg-background/85 p-1 shadow-lg shadow-black/5 backdrop-blur-lg backdrop-saturate-150 transition-colors duration-300 [view-transition-name:bottom-nav] reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
	>
		<!-- One capsule that slides between tabs rather than one per tab, so a switch
		     reads as motion from the old tab to the new one. It spans exactly one of the
		     five equal columns, so translating by its own width steps one tab. The tint is
		     strong enough to track mid-slide, so the active label steps down to primary-700
		     in light mode, the `tonal` button's trick: primary-600 measured 4.38:1 on a mere
		     /10, primary-700 is 5.6:1 on this /12. Dark keeps the token (5.3:1 on /20). -->
		<span
			aria-hidden="true"
			class={[
				'absolute inset-y-1 left-1 w-[calc((100%-0.5rem)/5)] rounded-full bg-primary/12 transition-[translate,opacity] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none dark:bg-primary/20',
				activeIndex === -1 && 'opacity-0'
			]}
			style:translate={indicatorShift}
		></span>

		{#each PRIMARY_NAV_ITEMS as item (item.href)}
			{@const { label, href, outlineIcon: Icon } = item}
			{@const active = isNavItemActive(activeUrl, item)}
			<!-- "Голосование" must fit one fifth of the pill: measured in-app it is ~62px at
			     10px, ~67px at 11px, ~73px at 12px. A tab gets ~67px on a 360px phone and
			     ~74px from 400px (where the pill's side margin grows from 8px to 12px). So
			     labels are 12px from 400px up (Material 3's nav-bar Label Medium), 11px with
			     tighter tracking from 360px (Apple's iOS minimum text size), and 10px below
			     360px, where the centred label may spill a pixel into its neighbour's
			     margin: that reads fine where an ellipsis would not. A shorter label was
			     rejected: the tab would stop matching the page title and the glossary term. -->
			<a
				href={resolve(href)}
				aria-current={active ? 'page' : undefined}
				class="group relative inline-flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-full text-3xs font-medium tracking-tighter transition-colors min-[22.5rem]:text-2xs min-[25rem]:text-xs min-[25rem]:tracking-tight"
				onclick={(event: MouseEvent) => {
					// Re-tapping the tab whose root you're already on returns to the top, the
					// native bottom-bar affordance. From a nested page (active by prefix, not
					// exact) the tap should navigate to the root instead, so gate on an exact match.
					if (activeUrl === resolve(href)) {
						event.preventDefault();
						scrollToTop();
					}
				}}
			>
				<!-- Colour and weight share the capsule's 300ms curve, so the old tab dims as
				     the capsule leaves it and the new one lights up as it arrives; a snap
				     would light the new label while the capsule still sits on the old tab. -->
				<Icon
					class={[
						'size-5 transition-[color,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-active:scale-90 motion-reduce:transition-none',
						active
							? 'text-primary-700 dark:text-primary'
							: 'text-muted-foreground group-hover:text-foreground'
					]}
				/>
				<span
					class={[
						'whitespace-nowrap transition-[color,font-weight] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none',
						active
							? 'font-semibold text-primary-700 dark:text-primary'
							: 'text-muted-foreground group-hover:text-foreground'
					]}
				>
					{label}
				</span>
			</a>
		{/each}
	</div>
</nav>
