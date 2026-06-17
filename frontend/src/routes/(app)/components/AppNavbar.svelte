<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { createApiClient } from '$lib/api';
	import NotificationBell from './NotificationBell.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearCache } from '$lib/utils/offlineCache';
	import {
		Avatar,
		Button,
		Dropdown,
		DropdownGroup,
		DropdownHeader,
		DropdownItem,
		Navbar,
		SidebarButton
	} from 'flowbite-svelte';
	import { ArrowRightToBracketOutline } from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';

	const client = createApiClient();

	// Pages expose their heading through `load` -> `page.data.title`.
	let pageTitle = $derived(page.data.title);

	let { user, toggleSidebar } = $props<{
		user: CurrentUserDTO | null;
		toggleSidebar: () => void;
	}>();

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

	const toastService = getToastService();
	const eventsClient = getEventsClient();

	async function handleLogout() {
		const { error, response } = await client.POST('/auth/logout');

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		// Drop the previous user's cached data so it can't surface for the next
		// account (or offline) on a shared device.
		await clearCache();

		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}
</script>

<!-- `fluid` makes the navbar content span the full width of the main area so the
	avatar/bell pin to the right edge; without it Flowbite caps content in a `container`. -->
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

	<div class="flex items-center gap-2 md:order-2">
		{#if user}
			<NotificationBell />
		{/if}
		{#if user}
			<Avatar id="avatar-menu" class="cursor-pointer">{avatarInitials}</Avatar>
			<Dropdown placement="bottom-end" triggeredBy="#avatar-menu">
				<DropdownHeader>
					<span class="block truncate text-sm font-medium text-gray-900 dark:text-white"
						>@{user.username}</span
					>
				</DropdownHeader>
				<DropdownGroup>
					<DropdownItem href="/profile">Профиль</DropdownItem>
					<DropdownItem onclick={handleLogout}>Выйти</DropdownItem>
				</DropdownGroup>
			</Dropdown>
		{:else}
			<Button href="/login" size="sm">
				<ArrowRightToBracketOutline class="me-2 h-4 w-4" />
				Войти
			</Button>
		{/if}
	</div>
</Navbar>
