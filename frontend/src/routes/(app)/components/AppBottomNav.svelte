<script lang="ts">
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { PRIMARY_NAV_ITEMS } from '#lib/data/nav.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getAppUpdateService } from '#lib/services/appUpdate.svelte.js';
	import { handleNavItemClick, hasUpdateDot, isNavItemActive, tabHref } from '#lib/utils/nav.js';

	interface Props {
		activeUrl: string;
		avatarSeed: string | null;
		lastSearches: Readonly<Record<string, string>>;
		scrollToTop: () => void;
	}

	let { activeUrl, avatarSeed, lastSearches, scrollToTop }: Props = $props();

	const appUpdate = getAppUpdateService();

	let activeIndex = $derived(
		PRIMARY_NAV_ITEMS.findIndex((item) => isNavItemActive(activeUrl, item))
	);
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

		{#each PRIMARY_NAV_ITEMS as item (item.href)}
			{const { label, href, outlineIcon: Icon } = $derived(item)}
			{const active = $derived(isNavItemActive(activeUrl, item))}
			{const updateDot = $derived(hasUpdateDot(href, appUpdate.available))}
			<a
				href={tabHref(href, lastSearches)}
				aria-current={active ? 'page' : undefined}
				class="group relative inline-flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-full text-3xs font-medium tracking-tighter transition-colors min-[22.5rem]:text-2xs min-[25rem]:text-xs min-[25rem]:tracking-tight"
				onclick={(event: MouseEvent) => handleNavItemClick(event, activeUrl, href, scrollToTop)}
			>
				<span class="relative">
					{#if href === 'profile' && avatarSeed}
						<UserAvatar
							seed={avatarSeed}
							class="size-5 transition-[scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-active:scale-90 motion-reduce:transition-none {active
								? 'ring-2 ring-primary-700 dark:ring-primary'
								: 'ring-1 ring-border'}"
						/>
					{:else}
						<Icon
							class={[
								'size-5 transition-[color,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-active:scale-90 motion-reduce:transition-none',
								active
									? 'text-primary-800 dark:text-primary-300'
									: 'text-gray-600 group-hover:text-foreground dark:text-muted-foreground'
							]}
						/>
					{/if}
					{#if updateDot}
						<span
							aria-hidden="true"
							class="absolute -top-0.5 -right-1 size-2.5 rounded-full border-2 border-background bg-primary"
						></span>
					{/if}
				</span>
				<span
					class={[
						'whitespace-nowrap transition-[color,font-weight] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none',
						active
							? 'font-semibold text-primary-800 dark:text-primary-300'
							: 'text-gray-600 group-hover:text-foreground dark:text-muted-foreground'
					]}
				>
					{label()}
				</span>
				{#if updateDot}
					<span class="sr-only">{m.nav_update_available()}</span>
				{/if}
			</a>
		{/each}
	</div>
</nav>
