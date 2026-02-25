<script lang="ts">
	import { page } from '$app/state';
	import ConnectionIndicator from '$lib/components/ConnectionIndicator.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { canManageSchedule } from '$lib/utils/permissions';
	import {
		BottomNav,
		BottomNavItem,
		DarkMode,
		Navbar,
		Sidebar,
		SidebarBrand,
		SidebarButton,
		SidebarGroup,
		SidebarItem,
		uiHelpers
	} from 'flowbite-svelte';
	import {
		CalendarWeekOutline,
		ClockArrowOutline,
		HomeSolid,
		ThumbsUpOutline,
		UserCircleOutline
	} from 'flowbite-svelte-icons';
	import '../app.css';

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
			class="sticky top-0 z-40 border-b border-gray-200/50 bg-white/80 px-4 py-2.5 backdrop-blur-md transition-colors duration-300 sm:px-6 dark:border-gray-700/50 dark:bg-gray-900/80"
		>
			<SidebarButton onclick={sidebarUi.toggle} class="md:hidden" />
			<div class="flex-1"></div>

			<div class="flex items-center gap-2 md:order-2">
				<ConnectionIndicator />
				<DarkMode class="rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-800" />
			</div>
		</Navbar>

		<section class="flex-1 overflow-y-auto scroll-smooth">
			<div class="mx-auto p-4 pb-24 md:p-6 md:pt-4 lg:p-8 lg:pt-4">
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
