<script lang="ts">
	import { page } from '$app/state';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { uiHelpers } from 'flowbite-svelte';
	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';

	let { data, children } = $props();

	let activeUrl = $derived(page.url.pathname);
	let user = $derived(data.user);

	const sidebarUi = uiHelpers();
	let isSidebarOpen = $derived(sidebarUi.isOpen);
	const closeSidebar = sidebarUi.close;
</script>

<div class="flex h-dvh w-full overflow-hidden bg-gray-50 dark:bg-gray-950">
	<SkipLink />

	<AppSidebar {user} {activeUrl} {isSidebarOpen} {closeSidebar} />

	<main class="relative flex flex-1 flex-col overflow-hidden">
		<AppNavbar {user} toggleSidebar={sidebarUi.toggle} />

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

	<AppBottomNav {activeUrl} />
</div>
