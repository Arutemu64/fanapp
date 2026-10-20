<script lang="ts">
	import { resolve } from '$app/paths';

	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '#lib/assets/logo.svg';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { PRIMARY_NAV_ITEMS } from '#lib/data/nav.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getAppUpdateService } from '#lib/services/appUpdate.svelte.js';
	import { handleNavItemClick, hasUpdateDot, isNavItemActive, tabHref } from '#lib/utils/nav.js';

	interface Props {
		activeUrl: string;
		/** The signed-in user's face for the Profile item; null keeps the generic icon. */
		avatarSeed: string | null;
		/** Each tab's last query string, keyed by resolved root (see `tabHref`). */
		lastSearches: Readonly<Record<string, string>>;
		scrollToTop: () => void;
	}

	let { activeUrl, avatarSeed, lastSearches, scrollToTop }: Props = $props();

	const appUpdate = getAppUpdateService();
</script>

<!-- Desktop twin of AppBottomNav: the same PRIMARY_NAV_ITEMS, so label, order and
     icons can't drift between the two. Everything without a tab of its own
     (feedback, the organizer toolbox, theme, logout) lives on the Profile page on both
     sizes, so phones need no hamburger drawer and this sidebar carries nothing extra. -->
<nav
	aria-label={m.nav_aria_label()}
	class="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-card p-4 md:flex"
>
	<a href={resolve('')} class="mb-6 flex items-center justify-center ps-0">
		<!-- The mark is pure black shapes on transparent (incl. a black "2026" pill with
			white text); `dark:invert` flips it to white shapes / a white pill with black
			text with no separate dark asset to maintain. -->
		<img src={logo} alt={m.app_name()} class="h-11 w-auto dark:invert" />
	</a>
	<div class="flex flex-col gap-1">
		{#each PRIMARY_NAV_ITEMS as item (item.href)}
			{const { label, href, outlineIcon: Icon } = $derived(item)}
			{const active = $derived(isNavItemActive(activeUrl, item))}
			{const updateDot = $derived(hasUpdateDot(href, appUpdate.available))}
			<a
				href={tabHref(href, lastSearches)}
				aria-current={active ? 'page' : undefined}
				class={[
					'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
					active
						? // primary-700 (not the semantic primary-600) so the label clears WCAG AA
							// on the primary/10 tint in light mode; dark keeps the lit brand hue.
							'bg-primary/10 text-primary-700 dark:text-primary'
						: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
				]}
				onclick={(event: MouseEvent) => handleNavItemClick(event, activeUrl, href, scrollToTop)}
			>
				{#if href === 'profile' && avatarSeed}
					<!-- Ringed, not tinted, for the reason given in AppBottomNav. -->
					<UserAvatar
						seed={avatarSeed}
						class="size-5 {active
							? 'ring-2 ring-primary-700 dark:ring-primary'
							: 'ring-1 ring-border'}"
					/>
				{:else}
					<Icon
						class={[
							'size-5 shrink-0 transition-colors',
							active
								? 'text-primary-700 dark:text-primary'
								: 'text-muted-foreground group-hover:text-foreground'
						]}
					/>
				{/if}
				<span>{label()}</span>
				{#if updateDot}
					<span aria-hidden="true" class="ms-auto size-2 rounded-full bg-primary"></span>
					<span class="sr-only">{m.nav_update_available()}</span>
				{/if}
			</a>
		{/each}
	</div>
</nav>
