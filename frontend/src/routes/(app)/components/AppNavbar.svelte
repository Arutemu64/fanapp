<script lang="ts">
	import { page } from '$app/state';
	import NotificationBell from './NotificationBell.svelte';
	import { Navbar, SidebarButton } from 'flowbite-svelte';
	import type { CurrentUserDTO } from '$lib/types/user';

	// Pages expose their heading through `load` -> `page.data.title`.
	let pageTitle = $derived(page.data.title);

	let { user, toggleSidebar } = $props<{
		user: CurrentUserDTO | null;
		toggleSidebar: () => void;
	}>();
</script>

<!-- `fluid` makes the navbar content span the full width of the main area so the
	bell pins to the right edge; without it Flowbite caps content in a `container`. -->
<Navbar
	fluid
	class="sticky top-0 z-40 border-b border-gray-200/50 bg-white/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] backdrop-blur-md transition-colors duration-300 sm:px-6 dark:border-gray-700/50 dark:bg-gray-900/80"
>
	<SidebarButton onclick={toggleSidebar} class="md:hidden" />
	<!-- Page title comes from each page's `load` via `page.data.title`; render it
		as the single page <h1> in the space the navbar used to leave empty. -->
	{#if pageTitle}
		<h1
			class="min-w-0 flex-1 truncate text-lg font-semibold text-gray-900 sm:text-xl dark:text-white"
		>
			{pageTitle}
		</h1>
	{:else}
		<div class="flex-1"></div>
	{/if}

	<!-- Profile/login moved to the bottom nav (mobile) and sidebar (desktop); the
		navbar now only keeps the glanceable notification bell. -->
	<div class="flex items-center gap-2 md:order-2">
		{#if user}
			<NotificationBell />
		{/if}
	</div>
</Navbar>
