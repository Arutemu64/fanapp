<script lang="ts">
	import type { PrimaryNavItem } from '#lib/data/nav.js';

	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getAppUpdateService } from '#lib/services/appUpdate.svelte.js';
	import { cn } from '#lib/utils.js';
	import { handleNavItemClick, hasUpdateDot, navItemCurrent, tabHref } from '#lib/utils/nav.js';

	interface Props {
		item: PrimaryNavItem;
		layout: 'sidebar' | 'bottom';
		activeUrl: string;
		avatarSeed: string | null;
		lastSearches: Readonly<Record<string, string>>;
		scrollToTop: () => void;
	}

	let { item, layout, activeUrl, avatarSeed, lastSearches, scrollToTop }: Props = $props();

	const appUpdate = getAppUpdateService();
	let { href, label, outlineIcon: Icon } = $derived(item);
	let active = $derived(navItemCurrent(activeUrl, item));
	let isBottom = $derived(layout === 'bottom');
	let updateDot = $derived(hasUpdateDot(href, appUpdate.available));
	const activeColor = 'text-primary-800 dark:text-primary-300';
	let bottomColor = $derived(
		active ? activeColor : 'text-muted-foreground group-hover:text-foreground'
	);
</script>

<a
	href={tabHref(href, lastSearches)}
	aria-current={active}
	class={[
		'relative flex-col items-center justify-center rounded-full',
		isBottom
			? [
					'group inline-flex min-w-0 gap-0.5 py-1 text-nav-label font-medium @max-[18em]:py-3.5',
					active && 'px-2 @max-[18em]:px-1'
				]
			: 'flex min-h-15 gap-1 p-2 text-center text-nav-label transition-colors motion-reduce:transition-none',
		!isBottom &&
			(active
				? ['font-semibold', activeColor]
				: 'font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground')
	]}
	onclick={(event: MouseEvent) => handleNavItemClick(event, activeUrl, href, scrollToTop)}
>
	<span class="relative">
		{#if href === 'profile' && avatarSeed}
			<UserAvatar
				seed={avatarSeed}
				class={cn(
					'size-6',
					isBottom &&
						'transition-[scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-active:scale-90 motion-reduce:transition-none',
					active ? 'ring-2 ring-primary-700 dark:ring-primary' : 'ring-1 ring-border'
				)}
			/>
		{:else}
			<Icon
				class={[
					'size-6',
					isBottom && [
						'transition-[color,scale] duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-active:scale-90 motion-reduce:transition-none',
						bottomColor
					]
				]}
				aria-hidden="true"
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
			'w-full wrap-anywhere hyphens-auto',
			isBottom && [
				'text-center transition-[color,font-weight] duration-300 ease-[cubic-bezier(0.2,0,0,1)] motion-reduce:transition-none',
				active && 'font-semibold',
				bottomColor
			]
		]}
	>
		{label()}
	</span>
	{#if updateDot}
		<span class="sr-only">{m.nav_update_available()}</span>
	{/if}
</a>
