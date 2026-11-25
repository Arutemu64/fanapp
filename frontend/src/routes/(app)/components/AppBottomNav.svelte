<script lang="ts">
	import { PRIMARY_NAV_ITEMS } from '#lib/data/nav.js';
	import { m } from '#lib/paraglide/messages.js';

	import AppNavLink from './AppNavLink.svelte';

	interface Props {
		activeIndex: number;
		activeUrl: string;
		avatarSeed: string | null;
		lastSearches: Readonly<Record<string, string>>;
		scrollToTop: () => void;
	}

	let { activeIndex, activeUrl, avatarSeed, lastSearches, scrollToTop }: Props = $props();

	let indicatorShift = $derived(`${Math.max(activeIndex, 0) * 100}% 0`);
</script>

<nav
	aria-label={m.nav_aria_label()}
	data-bottom-nav
	data-sveltekit-preload-code="viewport"
	class="pointer-events-none fixed inset-x-0 bottom-(--bottom-nav-gap) z-(--z-overlay) px-2 select-none [-webkit-touch-callout:none] min-[25rem]:px-3 md:hidden"
>
	<div
		class="pointer-events-auto relative mx-auto grid h-16 max-w-md grid-cols-5 rounded-full border border-border/60 bg-background/85 p-1 shadow-lg shadow-black/5 backdrop-blur-lg backdrop-saturate-150 transition-colors duration-300 [view-transition-name:bottom-nav] reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
	>
		<span
			aria-hidden="true"
			class={[
				'absolute inset-y-1 left-1 w-[calc((100%-0.5rem)/5)] rounded-full bg-primary/12 transition-[translate,opacity] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none dark:bg-primary/20',
				activeIndex === -1 && 'opacity-0'
			]}
			style:translate={indicatorShift}
		></span>

		{#each PRIMARY_NAV_ITEMS as item, index (item.href)}
			<AppNavLink
				{item}
				layout="bottom"
				active={index === activeIndex}
				{activeUrl}
				{avatarSeed}
				{lastSearches}
				{scrollToTop}
			/>
		{/each}
	</div>
</nav>
