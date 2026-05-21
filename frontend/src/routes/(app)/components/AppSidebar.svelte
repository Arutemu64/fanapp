<script lang="ts">
	import { canManageSchedule } from '$lib/utils/permissions';
	import {
		Sidebar,
		SidebarBrand,
		SidebarDropdownWrapper,
		SidebarGroup,
		SidebarItem
	} from 'flowbite-svelte';
	import {
		AdjustmentsHorizontalOutline,
		BullhornOutline,
		CalendarWeekOutline,
		ClockArrowOutline,
		FileImportOutline,
		HomeSolid,
		MapPinAltOutline,
		ShieldOutline,
		ThumbsUpOutline,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';

	let { user, activeUrl, isSidebarOpen, closeSidebar } = $props<{
		user: any;
		activeUrl: string;
		isSidebarOpen: boolean;
		closeSidebar: () => void;
	}>();

	// Show helper/org navigation from the current SSR-loaded user role.
	let canSeeVolunteerMenu = $derived(user?.role === 'helper' || user?.role === 'org');
	let canSeeOrganizerMenu = $derived(user?.role === 'org');
</script>

{#snippet sidebarLinks()}
	<SidebarBrand>
		<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
			ФАН ФАН
		</span>
	</SidebarBrand>
	<SidebarGroup>
		<SidebarItem label="Главная" href="/">
			{#snippet icon()}
				<HomeSolid
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
				<SidebarItem label="Настройки фестиваля" href="/org/settings">
					{#snippet icon()}
						<!-- This matches the page action: importing a schedule file. -->
						<AdjustmentsHorizontalOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
				<SidebarItem label="Импорт расписания" href="/org/import_schedule">
					{#snippet icon()}
						<!-- This matches the page action: importing a schedule file. -->
						<FileImportOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
				<SidebarItem label="Рассылка уведомлений" href="/org/broadcast">
					{#snippet icon()}
						<BullhornOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
			</SidebarDropdownWrapper>
		{/if}
	</SidebarGroup>
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
