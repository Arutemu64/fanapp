<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { client } from '$lib/api';
	import ConnectionIndicator from '$lib/components/ConnectionIndicator.svelte';
	import NotificationBell from '$lib/components/NotificationBell.svelte';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import {
		Avatar,
		Button,
		DarkMode,
		Dropdown,
		DropdownGroup,
		DropdownHeader,
		DropdownItem,
		Navbar,
		SidebarButton
	} from 'flowbite-svelte';

	let { user, toggleSidebar } = $props<{
		user: any;
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
		const { error } = await client.POST('/auth/logout');

		if (error) {
			toastService.error(error);
			return;
		}

		await goto(resolve('/'), { invalidateAll: true });
		eventsClient?.restart();
	}
</script>

<Navbar
	class="sticky top-0 z-40 border-b border-gray-200/50 bg-white/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] backdrop-blur-md transition-colors duration-300 sm:px-6 dark:border-gray-700/50 dark:bg-gray-900/80"
>
	<SidebarButton onclick={toggleSidebar} class="md:hidden" />
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
					<DropdownItem onclick={handleLogout}>Выйти</DropdownItem>
				</DropdownGroup>
			</Dropdown>
		{:else}
			<Button href="/login" size="sm">Войти</Button>
		{/if}
	</div>
</Navbar>
