<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { client } from '$lib/api';
	import ConnectionIndicator from '$lib/components/ConnectionIndicator.svelte';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { canManageSchedule } from '$lib/utils/permissions';
	import {
		Avatar,
		BottomNav,
		BottomNavItem,
		Button,
		DarkMode,
		Dropdown,
		DropdownDivider,
		DropdownGroup,
		DropdownHeader,
		DropdownItem,
		Navbar,
		Sidebar,
		SidebarBrand,
		SidebarButton,
		SidebarDropdownWrapper,
		SidebarGroup,
		SidebarItem,
		uiHelpers
	} from 'flowbite-svelte';
	import {
		AdjustmentsHorizontalOutline,
		CalendarWeekOutline,
		ClockArrowOutline,
		FileImportOutline,
		HomeSolid,
		MapPinAltOutline,
		ShieldOutline,
		ThumbsUpOutline,
		UsersGroupOutline
	} from 'flowbite-svelte-icons';

	let { data, children } = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);
	// Show helper/org navigation from the current SSR-loaded user role.
	let canSeeVolunteerMenu = $derived(user?.role === 'helper' || user?.role === 'org');
	let canSeeOrganizerMenu = $derived(user?.role === 'org');
	let avatarInitials = $derived.by(() => {
		const rawUsername = user?.username?.trim();

		if (!rawUsername) {
			return 'П';
		}

		const username = rawUsername.replace(/^@/, '');

		if (!username) {
			return 'П';
		}

		const parts = username.split(/[\s._-]+/).filter(Boolean);

		if (parts.length >= 2) {
			const firstInitial = parts[0]?.[0] ?? '';
			const secondInitial = parts[1]?.[0] ?? '';

			return `${firstInitial}${secondInitial}`.toUpperCase();
		}

		return username.slice(0, 2).toUpperCase();
	});

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;

	const toastService = getToastService();
	const eventsClient = getEventsClient();

	async function handleLogout() {
		const { error } = await client.POST('/auth/logout');

		if (error) {
			toastService.error(error);
			return;
		}

		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}
</script>

{#snippet sidebarLinks()}
	<SidebarBrand>
		<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
			FAN FAN
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
			<SidebarDropdownWrapper label="Для волонтеров" btnClass="p-2">
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
			<SidebarDropdownWrapper label="Для организаторов" btnClass="p-2">
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
			</SidebarDropdownWrapper>
		{/if}
	</SidebarGroup>
{/snippet}

<div class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<SkipLink />

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

	<main class="relative flex flex-1 flex-col overflow-hidden">
		<Navbar
			class="sticky top-0 z-40 border-b border-gray-200/50 bg-white/80 px-4 py-2.5 backdrop-blur-md transition-colors duration-300 sm:px-6 dark:border-gray-700/50 dark:bg-gray-900/80"
		>
			<SidebarButton onclick={sidebarUi.toggle} class="md:hidden" />
			<div class="flex-1"></div>

			<div class="flex items-center gap-2 md:order-2">
				<ConnectionIndicator />
				{#if user}
					<NotificationBell />
				{/if}
				<DarkMode class="rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-800" />
				{#if user}
					<Avatar id="avatar-menu" class="cursor-pointer">{avatarInitials}</Avatar>
					<Dropdown placement="bottom-end" triggeredBy="#avatar-menu">
						<DropdownHeader>
							<span class="block text-sm text-gray-900 dark:text-white"
								>{user.first_name || 'Пользователь'}</span
							>
							{#if user.username}
								<span class="block truncate text-sm font-medium">@{user.username}</span>
							{/if}
						</DropdownHeader>
						<DropdownGroup>
							<DropdownItem href="/profile">Профиль</DropdownItem>
							<DropdownDivider />
							<DropdownItem onclick={handleLogout}>Выйти</DropdownItem>
						</DropdownGroup>
					</Dropdown>
				{:else}
					<Button href="/login" size="sm">Войти</Button>
				{/if}
			</div>
		</Navbar>

		<section
			id="main-content"
			tabindex="-1"
			class="relative flex-1 overflow-y-auto scroll-smooth focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
		>
			<ToastContainer />
			<div class="mx-auto max-w-7xl p-4 pb-24 md:p-6 md:pt-4 lg:p-8 lg:pt-4">
				{@render children()}
			</div>
		</section>
	</main>

	<BottomNav
		{activeUrl}
		position="fixed"
		class="bottom-0 left-0 z-50 w-full border-t border-gray-200 bg-white md:hidden dark:border-gray-800 dark:bg-gray-900"
		classes={{ inner: 'grid-cols-4' }}
	>
		<BottomNavItem btnName="Главная" href="/">
			<HomeSolid
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
		<BottomNavItem btnName="Расписание" href="/schedule">
			<CalendarWeekOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
		<!-- Mirror the sidebar shortcut here so the map stays visible above the fixed mobile nav. -->
		<BottomNavItem btnName="Карта" href="/map">
			<MapPinAltOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
		<BottomNavItem btnName="Голосование" href="/voting">
			<ThumbsUpOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
	</BottomNav>
</div>
