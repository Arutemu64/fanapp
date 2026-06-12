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
		BullhornOutline,
		CalendarWeekOutline,
		ClockArrowOutline,
		FileImportOutline,
		HomeOutline,
		MapPinAltOutline,
		ShieldOutline,
		ThumbsUpOutline,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';
	import ThemeToggle from './ThemeToggle.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';

	let { user, activeUrl, isSidebarOpen, closeSidebar } = $props<{
		user: CurrentUserDTO | null;
		activeUrl: string;
		isSidebarOpen: boolean;
		closeSidebar: () => void;
	}>();

	// Gate staff navigation by effective permissions (ORG resolves via the
	// wildcard), matching the backend's per-permission checks. Show each
	// dropdown only when the user can reach at least one item inside it.
	let canSeeVolunteerMenu = $derived(canManageSchedule(user));
	let canSeeOrganizerMenu = $derived(
		canManageSettings(user) || canImportSchedule(user) || canSendNotifications(user)
	);
</script>

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
			{#if canSeeVolunteerMenu}
				<SidebarDropdownWrapper label="Для волонтеров" classes={{ btn: 'p-2' }}>
					{#snippet icon()}
						<UsersGroupOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
					{#if canManageSchedule(user)}
						<SidebarItem label="Изменения расписания" href="/schedule/changes">
							{#snippet icon()}
								<ClockArrowOutline
									class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
								/>
							{/snippet}
						</SidebarItem>
					{/if}
				</SidebarDropdownWrapper>
			{/if}
			{#if canSeeOrganizerMenu}
				<SidebarDropdownWrapper label="Для организаторов" classes={{ btn: 'p-2' }}>
					{#snippet icon()}
						<ShieldOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
					<!-- Keep festival controls together so organizers can find them quickly on mobile. -->
					{#if canManageSettings(user)}
						<SidebarItem label="Настройки фестиваля" href="/org/settings">
							{#snippet icon()}
								<AdjustmentsHorizontalOutline
									class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
								/>
							{/snippet}
						</SidebarItem>
					{/if}
					{#if canImportSchedule(user)}
						<SidebarItem label="Импорт расписания" href="/org/import_schedule">
							{#snippet icon()}
								<!-- This matches the page action: importing a schedule file. -->
								<FileImportOutline
									class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
								/>
							{/snippet}
						</SidebarItem>
					{/if}
					{#if canSendNotifications(user)}
						<SidebarItem label="Рассылка уведомлений" href="/org/broadcast">
							{#snippet icon()}
								<BullhornOutline
									class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
								/>
							{/snippet}
						</SidebarItem>
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
