<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component } from 'svelte';

	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '$lib/assets/logo.svg';
	import { isActivePath } from '$lib/utils/nav';
	import { isOrg } from '$lib/utils/permissions';
	import { Sidebar, SidebarBrand, SidebarGroup, SidebarItem } from 'flowbite-svelte';
	import {
		AnnotationOutline,
		AnnotationSolid,
		CalendarWeekOutline,
		CalendarWeekSolid,
		HomeOutline,
		HomeSolid,
		MapPinAltOutline,
		MapPinAltSolid,
		ThumbsUpOutline,
		ThumbsUpSolid,
		ToolsOutline
	} from 'flowbite-svelte-icons';

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
     in primary, idle outline icon in gray with a primary hover. -->
{#snippet navLink(label: string, href: string, OutlineIcon: Component, SolidIcon: Component)}
	{@const active = isActivePath(activeUrl, href)}
	<SidebarItem
		{label}
		{href}
		{active}
		onclick={(event: MouseEvent) => {
			// Mirror the bottom nav: re-tapping the current root eases back to the top,
			// only on an exact match so a nested page still navigates to the root.
			if (activeUrl === href) {
				event.preventDefault();
				scrollToTop();
			}
			// SidebarItem's built-in drawer close runs through its own onclick, which
			// this prop overrides, so close the mobile drawer here. A no-op on the
			// static desktop sidebar, which has no drawer state to close.
			closeSidebar();
		}}
	>
		{#snippet icon()}
			{#if active}
				<SolidIcon class="h-5 w-5 shrink-0 text-primary-600 dark:text-primary-400" />
			{:else}
				<OutlineIcon
					class="h-5 w-5 shrink-0 text-gray-500 transition duration-75 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
				/>
			{/if}
		{/snippet}
	</SidebarItem>
{/snippet}

<!-- `isMobile` slims the hamburger sheet: on phones the four primary
     destinations live in the bottom nav, so the drawer only carries what the
     bottom nav can't (feedback, the org toolbox, theme). Desktop has no
     bottom nav, so its static sidebar keeps the full set. -->
{#snippet sidebarLinks(isMobile: boolean)}
	<div class="flex h-full flex-col">
		<!-- SidebarBrand renders a plain <a href="/"> and, unlike SidebarItem, never reads
		     closeSidebar off the sidebar context — without this the drawer would stay open
		     on top of the page it just navigated to. The static desktop sidebar has no
		     drawer state to close. -->
		<SidebarBrand onclick={isMobile ? closeSidebar : undefined} class="justify-center ps-0">
			<!-- The mark is pure black shapes on transparent (incl. a black "2026" pill with
				white text); `dark:invert` flips it to white shapes / a white pill with black
				text with no separate dark asset to maintain. -->
			<img src={logo} alt="ФАН ФАН" class="h-11 w-auto dark:invert" />
		</SidebarBrand>
		<SidebarGroup>
			{#if !isMobile}
				{@render navLink('Главная', '/', HomeOutline, HomeSolid)}
				{@render navLink('Программа', '/schedule', CalendarWeekOutline, CalendarWeekSolid)}
				<!-- Order matches the bottom nav: voting before the map. -->
				{@render navLink('Голосование', '/voting', ThumbsUpOutline, ThumbsUpSolid)}
				<!-- Keep the venue map in the main navigation so it is reachable in one tap. -->
				{@render navLink('Карта', '/map', MapPinAltOutline, MapPinAltSolid)}
			{/if}
			{#if user}
				{@render navLink('Обратная связь', '/feedback', AnnotationOutline, AnnotationSolid)}
			{/if}
			{#if showTools}
				<!-- ToolsOutline has no solid twin; reuse navLink with the same icon in
				     both slots so the active state is a primary tint, not a shape swap. -->
				{@render navLink('Инструменты', '/tools', ToolsOutline, ToolsOutline)}
			{/if}
		</SidebarGroup>
		<div class="mt-auto border-t border-gray-200 p-3 dark:border-gray-700">
			<ThemeToggle />
		</div>
	</div>
{/snippet}

<!-- Flowbite renders <aside>, a `complementary` landmark; these hold only navigation. A
     real <nav> would beat the role override, but wrapping a flex child the layout sizes
     costs more than it buys. Labels omit "навигация" — the role is announced already. The
     drawer's differs from the bottom nav's because both are exposed while it is open. -->
<!-- The open drawer is modal: both its panel and its backdrop must sit above the
     bottom nav (--z-overlay, AppBottomNav), so the scrim covers it and its links
     aren't tappable through the overlay. Flowbite's theme ships the panel at z-50
     (ties with the bottom nav, which then wins on DOM order) and the backdrop at
     z-40 (below it entirely); both are lifted to the --z-modal rung — see
     docs/frontend.md "Z-Index Scale". -->
<Sidebar
	{activeUrl}
	backdrop={true}
	isOpen={isSidebarOpen}
	{closeSidebar}
	position="fixed"
	role="navigation"
	ariaLabel="Меню"
	class="z-(--z-modal) h-full md:hidden"
	classes={{ backdrop: 'z-(--z-modal)' }}
>
	{@render sidebarLinks(true)}
</Sidebar>

<Sidebar
	{activeUrl}
	backdrop={false}
	position="static"
	role="navigation"
	ariaLabel="Разделы"
	class="hidden h-full shrink-0 border-r border-gray-200 md:block dark:border-gray-700"
>
	{@render sidebarLinks(false)}
</Sidebar>
