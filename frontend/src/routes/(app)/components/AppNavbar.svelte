<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { createApiClient } from '$lib/api';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { setAppBadgeCount } from '$lib/utils/appBadge';
	import { clearUserCache } from '$lib/utils/offlineCache';
	import { getAvatarInitials } from '$lib/utils/users';
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

	import NotificationBell from './NotificationBell.svelte';

	const client = createApiClient();

	// Pages expose their heading through `load` -> `page.data.title`.
	let pageTitle = $derived(page.data.title);

	interface Props {
		user: CurrentUserDTO | null;
		toggleSidebar: () => void;
	}

	let { user, toggleSidebar }: Props = $props();

	let avatarInitials = $derived(getAvatarInitials(user?.username));
	let isAvatarMenuOpen = $state(false);

	const toastService = getToastService();
	const eventsClient = getEventsClient();

	async function handleLogout() {
		const { error, response } = await client.POST('/auth/logout');

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		// Drop the previous user's cached data so it can't surface for the next
		// account (or offline) on a shared device. Universal caches (e.g. schedule)
		// stay warm by design.
		await clearUserCache();
		// The bell unmounts with the session, so clear its app-icon badge here —
		// otherwise the previous user's unread count would linger on the icon.
		setAppBadgeCount(0);

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
			<!-- Flowbite's Avatar renders a div with a hardcoded role="button" but no
				keydown handling, so it claims a role it doesn't implement: Enter and
				Space do nothing on it. The real <button> is the trigger (Popper binds to
				this id), and the Avatar rides along as decoration — its initials would
				otherwise announce as the button's name instead of "Меню профиля". -->
			<button
				id="avatar-menu"
				type="button"
				aria-label="Меню профиля"
				aria-haspopup="true"
				aria-expanded={isAvatarMenuOpen}
				class="rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
			>
				<Avatar aria-hidden="true" class="cursor-pointer">{avatarInitials}</Avatar>
			</button>
			<Dropdown placement="bottom-end" triggeredBy="#avatar-menu" bind:isOpen={isAvatarMenuOpen}>
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
