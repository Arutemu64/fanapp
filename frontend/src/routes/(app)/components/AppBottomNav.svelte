<script lang="ts">
	import { resolve } from '$app/paths';
	import { PRIMARY_NAV_ITEMS } from '$lib/data/nav';
	import { isNavItemActive } from '$lib/utils/nav';

	interface Props {
		activeUrl: string;
		scrollToTop: () => void;
	}

	let { activeUrl, scrollToTop }: Props = $props();
</script>

<!-- Frosted-glass surface (translucent bg + backdrop blur) matching AppNavbar: content
     scrolls under it rather than stopping at an opaque band. -->
<nav
	aria-label="Разделы"
	class="fixed inset-x-0 bottom-0 z-(--z-overlay) grid h-16 grid-cols-5 border-t border-border/50 bg-background/80 pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] backdrop-blur-md transition-colors duration-300 md:hidden"
>
	{#each PRIMARY_NAV_ITEMS as item (item.href)}
		{@const { label, href, outlineIcon: Icon } = item}
		{@const active = isNavItemActive(activeUrl, item)}
		<!-- Five columns leave 72px each on a 360px phone, and "Голосование" set at 12px
		     is ~77px wide, so it ran into its neighbour. Below 400px the labels step down
		     to 11px with tight tracking (~68px); from
		     400px up a column clears the 12px label. -->
		<a
			href={resolve(href)}
			aria-current={active ? 'page' : undefined}
			class="group inline-flex min-w-0 flex-col items-center justify-center px-0.5 py-1 text-[0.6875rem] font-medium tracking-tight transition-colors min-[25rem]:text-xs min-[25rem]:tracking-normal"
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
			<Icon
				class={[
					'mb-1 size-5 transition-colors',
					active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
				]}
			/>
			<span
				class={[
					active
						? 'font-semibold text-primary'
						: 'text-muted-foreground group-hover:text-foreground'
				]}
			>
				{label}
			</span>
		</a>
	{/each}
</nav>
