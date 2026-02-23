<script lang="ts">
	import '../app.css';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import ConnectionIndicator from '$lib/components/ConnectionIndicator.svelte';
	import { page } from '$app/state';
	import {
		Sidebar,
		SidebarGroup,
		SidebarItem,
		SidebarButton,
		SidebarBrand,
		BottomNav,
		BottomNavItem,
		Navbar,
		Dropdown,
		DropdownItem,
		DropdownGroup,
		DarkMode,
		Avatar,
		DropdownHeader,
		uiHelpers
	} from 'flowbite-svelte';
	import {
		HomeSolid,
		CalendarWeekOutline,
		ThumbsUpOutline,
		ClockArrowOutline,
		UserCircleOutline
	} from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { canManageSchedule } from '$lib/utils/permissions';
	import { toastService } from '$lib/stores/toasts.svelte';
	import { goto } from '$app/navigation';

	async function handleLogout() {
		const { data, error, response } = await client.POST('/auth/logout');

		if (error) {
			toastService.error(error);
			return;
		}

		goto('/', {invalidateAll: true});
	}

	let { data, children } = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;
</script>

{#snippet sidebarLinks()}
	<SidebarBrand>
		<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
			FAN App
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
		<SidebarItem label="Голосование" href="/voting">
			{#snippet icon()}
				<ThumbsUpOutline
					class="h-5 w-5 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white"
				/>
			{/snippet}
		</SidebarItem>
		<SidebarItem label="Профиль" href="/profile">
			{#snippet icon()}
				<UserCircleOutline
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
{/snippet}

<div class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
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
			class="sticky top-0 z-40 border-b border-gray-200 bg-white px-4 py-2.5 sm:px-6 dark:border-gray-700 dark:bg-gray-900"
		>
			<SidebarButton onclick={sidebarUi.toggle} class="md:hidden" />
			<div class="flex-1"></div>

			<div class="flex items-center gap-2 md:order-2">
				<ConnectionIndicator />
				<DarkMode />
				{#if user}
					<Avatar id="avatar-menu" />
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

		<section class="flex-1 overflow-y-auto scroll-smooth">
			<div class="mx-auto p-4 pb-24 md:p-6 lg:p-8">
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
		<BottomNavItem btnName="Голосование" href="/voting">
			<ThumbsUpOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
		<BottomNavItem btnName="Профиль" href="/profile">
			<UserCircleOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		</BottomNavItem>
	</BottomNav>
</div>
<ToastContainer />
