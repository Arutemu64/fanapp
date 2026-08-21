<script lang="ts">
	import { PRIMARY_NAV_ITEMS } from '$lib/data/nav';
	import { isActivePath } from '$lib/utils/nav';
	import { BottomNav, BottomNavItem } from 'flowbite-svelte';

	interface Props {
		activeUrl: string;
		scrollToTop: () => void;
	}

	let { activeUrl, scrollToTop }: Props = $props();
</script>

<!-- BottomNav renders a plain <div>, so the bar is no landmark until `role` names it. The
     label omits "навигация" — the role is announced already — and matches the desktop
     sidebar's: same navigation at the opposite breakpoint, never in the tree together. -->
<BottomNav
	{activeUrl}
	position="fixed"
	role="navigation"
	aria-label="Разделы"
	class="z-(--z-overlay) pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] md:hidden dark:border-gray-700 dark:bg-gray-900"
	classes={{ inner: 'grid-cols-4' }}
>
	{#each PRIMARY_NAV_ITEMS as { label, href, outlineIcon: OutlineIcon, solidIcon: SolidIcon } (href)}
		{@const active = isActivePath(activeUrl, href)}
		<BottomNavItem
			btnName={label}
			{href}
			aria-current={active ? 'page' : undefined}
			onclick={(event: MouseEvent) => {
				// Re-tapping the tab whose root you're already on returns to the top, the
				// native bottom-bar affordance. From a nested page (active by prefix, not
				// exact) the tap should navigate to the root instead, so gate on an exact match.
				if (activeUrl === href) {
					event.preventDefault();
					scrollToTop();
				}
			}}
		>
			{#if active}
				<SolidIcon class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
			{:else}
				<OutlineIcon
					class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
				/>
			{/if}
		</BottomNavItem>
	{/each}
</BottomNav>
