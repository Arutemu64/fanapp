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

	let navHeight = $state(0);
	let dock = $state<HTMLDivElement>();
	let indicator = $state({ left: 0, width: 0 });

	$effect(() => {
		if (!navHeight) return;

		const root = document.documentElement;
		root.style.setProperty('--bottom-nav-height', `${navHeight}px`);
		return () => root.style.removeProperty('--bottom-nav-height');
	});

	$effect(() => {
		const container = dock;
		if (!container) return;
		const links = container.querySelectorAll<HTMLAnchorElement>(':scope > a');
		const activeLink = links[activeIndex];
		if (!activeLink) return;

		const measure = () => {
			const { left, width } = activeLink.getBoundingClientRect();
			indicator = {
				left: left - container.getBoundingClientRect().left - container.clientLeft,
				width
			};
		};

		measure();
		const observer = new ResizeObserver(measure);
		for (const link of links) observer.observe(link, { box: 'border-box' });
		return () => observer.disconnect();
	});
</script>

<nav
	aria-label={m.nav_aria_label()}
	data-bottom-nav
	data-sveltekit-preload-code="viewport"
	class="@container pointer-events-none fixed inset-x-0 bottom-(--bottom-nav-gap) z-(--z-overlay) bottom-nav-insets select-none [-webkit-touch-callout:none] md:hidden"
>
	<div
		bind:this={dock}
		bind:offsetHeight={navHeight}
		class="pointer-events-auto relative mx-auto grid min-h-16 max-w-md grid-cols-[repeat(5,minmax(min(2.75rem,20%),auto))] rounded-full border border-border/60 bg-background/85 p-1 shadow-lg shadow-black/5 backdrop-blur-lg backdrop-saturate-150 transition-colors duration-300 [view-transition-name:bottom-nav] @max-[18em]:rounded-4xl reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
	>
		<span
			data-bottom-nav-indicator
			aria-hidden="true"
			class={[
				'absolute inset-y-1 left-0 rounded-full bg-primary/12 transition-[translate,width,opacity] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none dark:bg-primary/20',
				(activeIndex === -1 || !indicator.width) && 'opacity-0'
			]}
			style:translate={`${indicator.left}px 0`}
			style:width={`${indicator.width}px`}
		></span>

		{#each PRIMARY_NAV_ITEMS as item (item.href)}
			<AppNavLink {item} layout="bottom" {activeUrl} {avatarSeed} {lastSearches} {scrollToTop} />
		{/each}
	</div>
</nav>
