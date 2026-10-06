<script lang="ts">
	import { resolve } from '$app/paths';
	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '$lib/assets/logo.svg';
	import { PRIMARY_NAV_ITEMS } from '$lib/data/nav';
	import { isNavItemActive } from '$lib/utils/nav';

	interface Props {
		activeUrl: string;
		scrollToTop: () => void;
	}

	let { activeUrl, scrollToTop }: Props = $props();
</script>

<!-- Desktop twin of AppBottomNav: the same PRIMARY_NAV_ITEMS, so label, order and
     icons can't drift between the two. Everything without a tab of its own
     (feedback, the org toolbox, theme, logout) lives on the Profile page on both
     sizes, so phones need no hamburger drawer and this sidebar carries nothing extra. -->
<aside
	role="navigation"
	aria-label="Разделы"
	class="hidden h-full w-64 shrink-0 flex-col border-r border-border bg-card p-4 md:flex"
>
	<a href={resolve('/')} class="mb-6 flex items-center justify-center ps-0">
		<!-- The mark is pure black shapes on transparent (incl. a black "2026" pill with
			white text); `dark:invert` flips it to white shapes / a white pill with black
			text with no separate dark asset to maintain. -->
		<img src={logo} alt="ФАН ФАН" class="h-11 w-auto dark:invert" />
	</a>
	<div class="flex flex-col gap-1">
		{#each PRIMARY_NAV_ITEMS as item (item.href)}
			{@const { label, href, outlineIcon: Icon } = item}
			{@const active = isNavItemActive(activeUrl, item)}
			<a
				href={resolve(href)}
				aria-current={active ? 'page' : undefined}
				class={[
					'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
					active
						? // primary-700 (not the semantic primary-600) so the label clears WCAG AA
							// on the primary/10 tint in light mode; dark keeps the lit brand hue.
							'bg-primary/10 text-primary-700 dark:text-primary'
						: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
				]}
				onclick={(event: MouseEvent) => {
					// Mirror the bottom nav: re-tapping the current root eases back to the top,
					// only on an exact match so a nested page still navigates to the root.
					if (activeUrl === href) {
						event.preventDefault();
						scrollToTop();
					}
				}}
			>
				<Icon
					class={[
						'size-5 shrink-0 transition-colors',
						active
							? 'text-primary-700 dark:text-primary'
							: 'text-muted-foreground group-hover:text-foreground'
					]}
				/>
				<span>{label}</span>
			</a>
		{/each}
	</div>
</aside>
