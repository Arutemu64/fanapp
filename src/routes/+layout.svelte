<script lang="ts">
	import '../app.css';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import type { FullUserDTO } from '$lib/types/user';
	import { page } from '$app/state';
	import { eventsClient } from '$lib/events.svelte';
	import {
		Sidebar,
		SidebarGroup,
		SidebarItem,
		SidebarButton,
		BottomNav,
		BottomNavItem,
		Navbar,
		Dropdown,
		DropdownItem,
		DropdownGroup,
		NavBrand,
		DarkMode,
		Avatar,
		DropdownHeader,
		uiHelpers
	} from 'flowbite-svelte';
	import { HomeSolid, CalendarWeekOutline, ThumbsUpOutline, ClockArrowOutline } from 'flowbite-svelte-icons';
	import { api } from '$lib/api';
	import { canManageSchedule } from '$lib/utils/permissions';

	async function handleLogout() {
		await api.post('/auth/logout', {});
		window.location.href = '/';
	}

	let { data, children } = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;
</script>

<div id="layout-shell" class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<!-- Mobile Sidebar (overlay) -->
	<Sidebar
		id="mobile-sidebar"
		{activeUrl}
		backdrop={true}
		isOpen={isSidebarOpen}
		{closeSidebar}
		params={{ x: -50, duration: 50 }}
		class="z-50 h-full"
		position="fixed"
		classes={{ nonactive: 'p-2', active: 'p-2' }}
	>
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
			<SidebarItem label="Голосование" href="/voting">
				{#snippet icon()}
					<ThumbsUpOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			{#if canManageSchedule(user)}
				<SidebarItem label="Изменения расписания" href="/schedule/changes">
					{#snippet icon()}
						<ClockArrowOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
			{/if}
		</SidebarGroup>
	</Sidebar>

	<!-- Desktop Sidebar (static) -->
	<Sidebar
		id="desktop-sidebar"
		{activeUrl}
		backdrop={false}
		params={{ x: -50, duration: 50 }}
		class="z-50 hidden h-full shrink-0 border-r border-gray-200 md:block dark:border-gray-800"
		position="static"
		classes={{ nonactive: 'p-2', active: 'p-2' }}
	>
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
			<SidebarItem label="Голосование" href="/voting">
				{#snippet icon()}
					<ThumbsUpOutline
						class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
					/>
				{/snippet}
			</SidebarItem>
			{#if canManageSchedule(user)}
				<SidebarItem label="Изменения расписания" href="/schedule/changes">
					{#snippet icon()}
						<ClockArrowOutline
							class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
						/>
					{/snippet}
				</SidebarItem>
			{/if}
		</SidebarGroup>
	</Sidebar>

	<BottomNav
		id="mobile-bottom-nav"
		{activeUrl}
		position="absolute"
		class="block md:hidden"
		classes={{ inner: 'grid-cols-3' }}
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
		<BottomNavItem btnName="Голосование" href="/voting">
			<ThumbsUpOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
	</BottomNav>

	<main id="main-viewport" class="relative flex flex-1 flex-col overflow-hidden">
		<Navbar
			id="top-navbar"
			class="sticky top-0 z-30 border-b border-gray-200 bg-white px-4 py-2.5 sm:px-6 dark:border-gray-700 dark:bg-gray-900"
		>
			<SidebarButton onclick={sidebarUi.toggle} class="md:hidden" />
			<NavBrand href="/">
				<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
					FAN App
				</span>
			</NavBrand>
			<div class="flex items-center gap-2 md:order-2">
				<DarkMode id="dark-mode-toggle" />
				{#if user}
					<Avatar
						id="avatar-menu"
						dot={{
							placement: 'bottom-right',
							color:
								eventsClient.connectionStatus === 'connected'
									? 'green'
									: eventsClient.connectionStatus === 'connecting'
										? 'yellow'
										: 'red'
						}}
					/>
				{:else}
					<a
						href="/login"
						class="inline-flex items-center gap-2 rounded-lg bg-primary-700 px-4 py-2 text-sm font-medium text-white hover:bg-primary-800 focus:ring-4 focus:ring-primary-300 focus:outline-none dark:bg-primary-600 dark:hover:bg-primary-700 dark:focus:ring-primary-800"
					>
						<span class="hidden sm:inline">Войти</span>
					</a>
				{/if}
			</div>
			{#if user}
				<Dropdown placement="bottom" triggeredBy="#avatar-menu">
					<DropdownHeader>
						<span class="block text-sm">{user.first_name}</span>
						<span class="block truncate text-sm font-medium">@{user.username}</span>
					</DropdownHeader>
					<DropdownGroup>
						<DropdownItem href="/link_ticket">Привязать билет</DropdownItem>
						<DropdownItem>Настройки</DropdownItem>
					</DropdownGroup>
					<DropdownItem onclick={handleLogout}>Выйти</DropdownItem>
				</Dropdown>
			{/if}
		</Navbar>

		<section id="scroll-container" class="flex-1 overflow-y-auto scroll-smooth">
			<div id="page-content" class="relative mx-auto p-4 pb-24 md:p-6 lg:p-8">
				{@render children()}
			</div>
		</section>
	</main>
</div>
<ToastContainer />
