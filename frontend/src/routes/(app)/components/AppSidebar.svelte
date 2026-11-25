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

	let indicatorShift = $derived(`0 calc(${Math.max(activeIndex, 0)} * (100% + var(--spacing)))`);
	const indicatorHeight = `calc((100% + var(--spacing)) / ${PRIMARY_NAV_ITEMS.length} - var(--spacing))`;
</script>

<div class="sticky top-0 hidden h-dvh shrink-0 items-start py-4 ps-4 md:flex lg:ps-6">
	<nav
		aria-label={m.nav_aria_label()}
		class="max-h-full w-26 overflow-x-hidden overflow-y-auto rounded-2xl bg-card p-2 shadow-xs ring-1 ring-foreground/10"
	>
		<div class="relative grid auto-rows-fr gap-1">
			<span
				aria-hidden="true"
				class={[
					'pointer-events-none absolute inset-x-0 top-0 rounded-full bg-primary/12 transition-[translate,opacity] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none dark:bg-primary/20',
					activeIndex === -1 && 'opacity-0'
				]}
				style:height={indicatorHeight}
				style:translate={indicatorShift}
			></span>
			{#each PRIMARY_NAV_ITEMS as item, index (item.href)}
				<AppNavLink
					{item}
					layout="sidebar"
					active={index === activeIndex}
					{activeUrl}
					{avatarSeed}
					{lastSearches}
					{scrollToTop}
				/>
			{/each}
		</div>
	</nav>
</div>
