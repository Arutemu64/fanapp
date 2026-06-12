<script lang="ts">
	import {
		canManageSchedule,
		canImportSchedule,
		canSendNotifications,
		canManageSettings
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
		ArrowRightToBracketOutline,
		BullhornOutline,
		CalendarWeekOutline,
		ClockArrowOutline,
		FileImportOutline,
		HomeOutline,
		LockOutline,
		MapPinAltOutline,
		ShieldOutline,
		ThumbsUpOutline,
		UserCircleOutline,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';
	import ThemeToggle from './ThemeToggle.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { Snippet } from 'svelte';

	let { user, activeUrl, isSidebarOpen, closeSidebar } = $props<{
		user: CurrentUserDTO | null;
		activeUrl: string;
		isSidebarOpen: boolean;
		closeSidebar: () => void;
	}>();

	// Staff (volunteers and organizers) see the staff dropdowns so they can
	// discover what exists; individual items are unlocked per effective
	// permission (ORG resolves via the wildcard). The backend still enforces
	// every action — locked items are a UX affordance only.
	let isStaff = $derived(user?.role === 'helper' || user?.role === 'org');
	let iconClass =
		'h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white';
</script>

<!-- A staff navigation entry: a real link when the user holds the permission,
     otherwise a non-navigable, greyed-out row with a lock badge + tooltip. -->
{#snippet staffLink(label: string, href: string, allowed: boolean, itemIcon: Snippet)}
	{#if allowed}
		<SidebarItem {label} {href}>
			{#snippet icon()}
				{@render itemIcon()}
			{/snippet}
		</SidebarItem>
	{:else}
		<li>
			<div
				class="flex cursor-not-allowed items-center rounded-lg p-2 text-gray-400 dark:text-gray-600"
				aria-disabled="true"
				title="Нужен доступ — попроси организатора"
			>
				{@render itemIcon()}
				<span class="ms-3 flex-1">{label}</span>
				<LockOutline class="h-4 w-4 shrink-0" />
			</div>
		</li>
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

{#snippet sidebarLinks()}
	<div class="flex h-full flex-col">
		<SidebarBrand>
			<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
				ФАН ФАН
			</span>
		</SidebarBrand>
		<SidebarGroup>
			<SidebarItem label="Главная" href="/">
				{#snippet icon()}
					<HomeOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			<SidebarItem label="Расписание" href="/schedule">
				{#snippet icon()}
					<CalendarWeekOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			<!-- Keep the venue map in the main navigation so it is reachable in one tap on mobile. -->
			<SidebarItem label="Карта" href="/map">
				{#snippet icon()}
					<MapPinAltOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			<SidebarItem label="Голосование" href="/voting">
				{#snippet icon()}
					<ThumbsUpOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			{#if user}
				<SidebarItem label="Обратная связь" href="/feedback">
					{#snippet icon()}
						<AnnotationOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
			{/if}
			<!-- Profile/login on desktop lives here since the bottom dock is mobile-only. -->
			{#if user}
				<SidebarItem label="Профиль" href="/profile">
					{#snippet icon()}
						<UserCircleOutline class={iconClass} />
					{/snippet}
				</SidebarItem>
			{:else}
				<SidebarItem label="Войти" href="/login">
					{#snippet icon()}
						<ArrowRightToBracketOutline class={iconClass} />
					{/snippet}
				</SidebarItem>
			{/if}
			{#if isStaff}
				<SidebarDropdownWrapper label="Для волонтеров" classes={{ btn: 'p-2' }}>
					{#snippet icon()}
						<UsersGroupOutline class={iconClass} />
					{/snippet}
					{@render staffLink(
						'Изменения расписания',
						'/schedule/changes',
						canManageSchedule(user),
						scheduleChangesIcon
					)}
				</SidebarDropdownWrapper>
				<SidebarDropdownWrapper label="Для организаторов" classes={{ btn: 'p-2' }}>
					{#snippet icon()}
						<ShieldOutline class={iconClass} />
					{/snippet}
					<!-- Keep festival controls together so organizers can find them quickly on mobile. -->
					{@render staffLink(
						'Настройки фестиваля',
						'/org/settings',
						canManageSettings(user),
						settingsIcon
					)}
					{@render staffLink(
						'Импорт расписания',
						'/org/import_schedule',
						canImportSchedule(user),
						importScheduleIcon
					)}
					{@render staffLink(
						'Рассылка уведомлений',
						'/org/broadcast',
						canSendNotifications(user),
						broadcastIcon
					)}
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
	{@render sidebarLinks()}
</Sidebar>

<Sidebar
	{activeUrl}
	backdrop={false}
	position="static"
	class="hidden h-full shrink-0 border-r border-gray-200 md:block dark:border-gray-800"
>
	{@render sidebarLinks()}
</Sidebar>
