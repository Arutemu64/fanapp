<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component, Snippet } from 'svelte';

	// Bundled (not static/) so Vite content-hashes it like the other brand assets.
	import logo from '$lib/assets/logo.svg';
	import { isActivePath } from '$lib/utils/nav';
	import {
		canGenerateTickets,
		canImportSchedule,
		canManageSchedule,
		canManageSettings,
		canRunSync,
		canSendNotifications
	} from '$lib/utils/permissions';
	import {
		Sidebar,
		SidebarBrand,
		SidebarDropdownWrapper,
		SidebarGroup,
		SidebarItem
	} from 'flowbite-svelte';
	import {
		AdjustmentsHorizontalOutline,
		AnnotationOutline,
		AnnotationSolid,
		BullhornOutline,
		CalendarWeekOutline,
		CalendarWeekSolid,
		ClockArrowOutline,
		FileImportOutline,
		HomeOutline,
		HomeSolid,
		LockOutline,
		MapPinAltOutline,
		MapPinAltSolid,
		RefreshOutline,
		ThumbsUpOutline,
		ThumbsUpSolid,
		TicketOutline,
		ToolsOutline
	} from 'flowbite-svelte-icons';

	import ThemeToggle from './ThemeToggle.svelte';

	interface Props {
		user: CurrentUserDTO | null;
		activeUrl: string;
		isSidebarOpen: boolean;
		closeSidebar: () => void;
	}

	let { user, activeUrl, isSidebarOpen, closeSidebar }: Props = $props();

	// The "Инструменты" dropdown is the staff toolbox. Role decides only whether to
	// show the toolbox at all — a visitor/participant can never hold these and would
	// just see a wall of locks. Every item inside is gated purely by effective
	// permission (incl. the former org-only tools), so helpers can discover what
	// they'd need access to. Permissions are not role-bound: any staff member can
	// hold any of them, and the backend enforces each action — locked rows are a
	// discovery affordance only.
	let isStaff = $derived(user?.role === 'helper' || user?.role === 'org');
	let iconClass =
		'h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white';
</script>

<!-- A primary destination row. Active state mirrors the bottom nav: solid icon
     in primary, idle outline icon in gray with a primary hover. -->
{#snippet navLink(label: string, href: string, OutlineIcon: Component, SolidIcon: Component)}
	{@const active = isActivePath(activeUrl, href)}
	<SidebarItem {label} {href} {active}>
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

<!-- A staff navigation entry: a real link when the user holds the permission,
     otherwise a non-navigable, greyed-out row with a lock badge + tooltip. -->
{#snippet staffLink(label: string, href: string, allowed: boolean, itemIcon: Snippet)}
	{#if allowed}
		<SidebarItem {label} {href} active={isActivePath(activeUrl, href)}>
			{#snippet icon()}
				{@render itemIcon()}
			{/snippet}
		</SidebarItem>
	{:else}
		<!-- No href keeps the row non-navigable; reusing SidebarItem keeps the
		     markup identical to unlocked rows so the lock badge causes no drift. -->
		<SidebarItem
			{label}
			aClass="flex items-center rounded-lg p-2 text-gray-400 cursor-not-allowed dark:text-gray-600"
			aria-disabled="true"
			title="Нужен доступ — попроси организатора"
		>
			{#snippet icon()}
				{@render itemIcon()}
			{/snippet}
			{#snippet subtext()}
				<LockOutline class="h-4 w-4 shrink-0" />
			{/snippet}
		</SidebarItem>
	{/if}
{/snippet}

{#snippet scheduleChangesIcon()}
	<ClockArrowOutline class={iconClass} />
{/snippet}
{#snippet settingsIcon()}
	<AdjustmentsHorizontalOutline class={iconClass} />
{/snippet}
{#snippet importScheduleIcon()}
	<FileImportOutline class={iconClass} />
{/snippet}
{#snippet broadcastIcon()}
	<BullhornOutline class={iconClass} />
{/snippet}
{#snippet generateTicketsIcon()}
	<TicketOutline class={iconClass} />
{/snippet}
{#snippet syncIcon()}
	<RefreshOutline class={iconClass} />
{/snippet}

<!-- `isMobile` slims the hamburger sheet: on phones the four primary
     destinations live in the bottom nav, so the drawer only carries what the
     bottom nav can't (feedback, staff/org sections, theme). Desktop has no
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
			{#if isStaff}
				<SidebarDropdownWrapper label="Инструменты" classes={{ btn: 'p-2' }}>
					{#snippet icon()}
						<ToolsOutline class={iconClass} />
					{/snippet}
					{@render staffLink(
						'Изменения программы',
						'/schedule/changes',
						canManageSchedule(user),
						scheduleChangesIcon
					)}
					{@render staffLink(
						'Настройки фестиваля',
						'/tools/settings',
						canManageSettings(user),
						settingsIcon
					)}
					{@render staffLink(
						'Импорт программы',
						'/tools/import_schedule',
						canImportSchedule(user),
						importScheduleIcon
					)}
					{@render staffLink(
						'Рассылка уведомлений',
						'/tools/broadcast',
						canSendNotifications(user),
						broadcastIcon
					)}
					{@render staffLink(
						'Генерация билетов',
						'/tools/generate_tickets',
						canGenerateTickets(user),
						generateTicketsIcon
					)}
					{@render staffLink('Синхронизация', '/tools/sync', canRunSync(user), syncIcon)}
				</SidebarDropdownWrapper>
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
