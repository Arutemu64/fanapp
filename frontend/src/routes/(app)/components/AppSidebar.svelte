<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '$lib/assets/logo.svg';
	import * as Sheet from '$lib/components/ui/sheet';
	import { PRIMARY_NAV_ITEMS } from '$lib/data/nav';
	import { isActivePath } from '$lib/utils/nav';
	import { isOrg } from '$lib/utils/permissions';
	import { MessageSquare, Wrench } from '@lucide/svelte';

	import ThemeToggle from './ThemeToggle.svelte';

	interface Props {
		user: CurrentUserDTO | null;
		activeUrl: string;
		isSidebarOpen: boolean;
		closeSidebar: () => void;
		scrollToTop: () => void;
	}

	let { user, activeUrl, isSidebarOpen, closeSidebar, scrollToTop }: Props = $props();

	// "Инструменты" is the organiser toolbox, now a single link to the /tools
	// dashboard instead of a dropdown of every tool — the sidebar stays short as
	// the tool list grows. The section is org-only for now; per-tool permission
	// gating lives on the dashboard, where locked tools show as a discovery cue.
	let showTools = $derived(isOrg(user));
</script>

<!-- A primary destination row. Active state mirrors the bottom nav: solid icon
     in primary, idle icon in gray with a primary hover. -->
{#snippet navLink(label: string, href: Pathname, Icon: Component)}
	{@const active = isActivePath(activeUrl, href)}
	<a
		href={resolve(href)}
		aria-current={active ? 'page' : undefined}
		class={[
			'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
			active
				? 'bg-primary/10 text-primary'
				: 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
		]}
		onclick={(event: MouseEvent) => {
			// Mirror the bottom nav: re-tapping the current root eases back to the top,
			// only on an exact match so a nested page still navigates to the root.
			if (activeUrl === href) {
				event.preventDefault();
				scrollToTop();
			}
			closeSidebar();
		}}
	>
		<Icon
			class={[
				'size-5 shrink-0 transition-colors',
				active ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'
			]}
		/>
		<span>{label}</span>
	</a>
{/snippet}

<!-- `isMobile` slims the hamburger sheet: on phones the four primary
     destinations live in the bottom nav, so the drawer only carries what the
     bottom nav can't (feedback, the org toolbox, theme). Desktop has no
     bottom nav, so its static sidebar keeps the full set. -->
{#snippet sidebarLinks(isMobile: boolean)}
	<div class="flex h-full flex-col p-4">
		<a
			href={resolve('/')}
			onclick={isMobile ? closeSidebar : undefined}
			class="mb-6 flex items-center justify-center ps-0"
		>
			<!-- The mark is pure black shapes on transparent (incl. a black "2026" pill with
				white text); `dark:invert` flips it to white shapes / a white pill with black
				text with no separate dark asset to maintain. -->
			<img src={logo} alt="ФАН ФАН" class="h-11 w-auto dark:invert" />
		</a>
		<div class="flex flex-col gap-1">
			{#if !isMobile}
				<!-- Same source as the bottom nav (PRIMARY_NAV_ITEMS), so label, order and
				     icons can't drift between the two surfaces. On phones these four live
				     in the bottom nav instead. -->
				{#each PRIMARY_NAV_ITEMS as item (item.href)}
					{@render navLink(item.label, item.href, item.outlineIcon)}
				{/each}
			{/if}
			{#if user}
				{@render navLink('Обратная связь', '/feedback', MessageSquare)}
			{/if}
			{#if showTools}
				{@render navLink('Инструменты', '/tools', Wrench)}
			{/if}
		</div>
		<div class="mt-auto border-t border-border pt-3">
			<ThemeToggle />
		</div>
	</div>
{/snippet}

<!-- Mobile drawer. The Sheet (Bits UI Dialog) owns the backdrop, focus trap,
     Escape, scroll-lock and stacking — the hand-rolled scrim it replaced trapped
     nothing, so keyboard users could tab out behind it. Controlled by the layout's
     `isSidebarOpen`; `onOpenChange` routes every dismiss back to closeSidebar. `p-0`
     because sidebarLinks brings its own padding. -->
<Sheet.Root
	open={isSidebarOpen}
	onOpenChange={(open) => {
		if (!open) closeSidebar();
	}}
>
	<Sheet.Content
		side="left"
		aria-label="Меню"
		showCloseButton={false}
		class="w-64 max-w-[80vw] gap-0 border-border bg-card p-0 md:hidden"
	>
		<Sheet.Title class="sr-only">Меню</Sheet.Title>
		<Sheet.Description class="sr-only">Навигация по разделам приложения.</Sheet.Description>
		{@render sidebarLinks(true)}
	</Sheet.Content>
</Sheet.Root>

<!-- Desktop sidebar -->
<aside
	role="navigation"
	aria-label="Разделы"
	class="hidden h-full w-64 shrink-0 flex-col border-r border-border bg-card md:flex"
>
	{@render sidebarLinks(false)}
</aside>
