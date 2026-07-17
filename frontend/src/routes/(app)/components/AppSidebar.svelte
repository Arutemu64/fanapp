<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Component, Snippet } from 'svelte';

	import { isActivePath } from '$lib/utils/nav';
	import {
		canGenerateTickets,
		canImportSchedule,
		canManageSchedule,
		canManageSettings,
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

	// All staff see the shared "Инструменты" dropdown so they can discover what
	// exists; individual items are unlocked per effective permission. The backend
	// still enforces every action — locked items are a UX affordance only.
	let isStaff = $derived(user?.role === 'helper' || user?.role === 'org');
	// Organizer-only tools stay hidden from volunteers entirely; this gates the
	// organizer subset within the shared dropdown.
	let isOrg = $derived(user?.role === 'org');
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

<!-- `isMobile` slims the hamburger sheet: on phones the four primary
     destinations live in the bottom nav, so the drawer only carries what the
     bottom nav can't (feedback, staff/org sections, theme). Desktop has no
     bottom nav, so its static sidebar keeps the full set. -->
{#snippet sidebarLinks(isMobile: boolean)}
	<div class="flex h-full flex-col">
		<SidebarBrand>
			<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
				ФАН ФАН
			</span>
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
					{#if isOrg}
						<!-- Organizer-only festival controls; hidden from volunteers entirely. -->
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
					{/if}
				</SidebarDropdownWrapper>
			{/if}
		</SidebarGroup>
		<div class="mt-auto border-t border-gray-200 p-3 dark:border-gray-700">
			<ThemeToggle />
		</div>
	</div>
{/snippet}

<Sidebar
	{activeUrl}
	backdrop={true}
	isOpen={isSidebarOpen}
	{closeSidebar}
	position="fixed"
	class="z-50 h-full md:hidden"
>
	{@render sidebarLinks(true)}
</Sidebar>

<Sidebar
	{activeUrl}
	backdrop={false}
	position="static"
	class="hidden h-full shrink-0 border-r border-gray-200 md:block dark:border-gray-700"
>
	{@render sidebarLinks(false)}
</Sidebar>
