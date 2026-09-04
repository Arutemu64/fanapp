<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { createApiClient } from '$lib/api';
	import * as Avatar from '$lib/components/ui/avatar';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { getEventsClient } from '$lib/services/events.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { setAppBadgeCount } from '$lib/utils/appBadge';
	import { clearUserCache } from '$lib/utils/offlineCache';
	import { markLogoutPending } from '$lib/utils/pendingLogout';
	import { getAvatarInitials } from '$lib/utils/users';
	import { LogOut, Menu, User } from '@lucide/svelte';

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

	const toastService = getToastService();
	const eventsClient = getEventsClient();
	const offline = getOfflineService();

	async function handleLogout() {
		// Offline: we can't reach the server to end the session, and the session
		// cookie is HttpOnly so JS can't clear it either. Record the intent — the
		// queued POST /auth/logout fires on reconnect (see pendingLogout) — and tear
		// down local state now so a shared device stops showing this account at once.
		if (!offline.isOnline) {
			markLogoutPending();
			await finishLogout();
			return;
		}

		const { error, response } = await client.POST('/auth/logout');

		if (error || !response.ok) {
			toastService.error(error);
			return;
		}

		await finishLogout();
	}

	async function finishLogout() {
		// Drop the previous user's cached data so it can't surface for the next
		// account (or offline) on a shared device. Universal caches (e.g. schedule)
		// stay warm by design.
		await clearUserCache();
		// The bell unmounts with the session, so clear its app-icon badge here —
		// otherwise the previous user's unread count would linger on the icon.
		setAppBadgeCount(0);

		await goto(resolve('/'), { invalidateAll: true });
		eventsClient.restart();
	}
</script>

<!-- Full width so the avatar/bell pin to the right edge.
	Positioning (overlay, z-index, hide-on-scroll) is owned by the (app) layout, which
	slides this bar with `top` to keep its backdrop blur intact. -->
<header
	class="flex items-center justify-between border-b border-border/50 bg-background/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] backdrop-blur-md transition-colors duration-300 sm:px-6"
>
	<Button
		variant="ghost"
		size="icon"
		onclick={toggleSidebar}
		aria-label="Открыть меню"
		class="mr-2 shrink-0 md:hidden"
	>
		<Menu class="size-5" />
	</Button>
	<!-- Page title comes from each page's `load` via `page.data.title`; render it
		as the single page <h1> in the space the navbar used to leave empty. -->
	{#if pageTitle}
		<h1 class="min-w-0 flex-1 truncate text-lg font-semibold text-foreground sm:text-xl">
			{pageTitle}
		</h1>
	{:else}
		<div class="flex-1"></div>
	{/if}

	<div class="flex items-center gap-2">
		{#if user}
			<NotificationBell />
		{/if}
		{#if user}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<button
							{...props}
							class="cursor-pointer rounded-full focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						>
							<Avatar.Root class="size-11">
								<Avatar.Fallback class="bg-primary/10 text-sm font-semibold text-primary">
									{avatarInitials}
								</Avatar.Fallback>
							</Avatar.Root>
						</button>
					{/snippet}
				</DropdownMenu.Trigger>
				<!-- sideOffset above the usual ~4 because the trigger is recessed inside the
					taller top bar: it must clear the bar's bottom padding, not just the avatar,
					or the menu tucks under the bar (which paints below it at a lower z-index). -->
				<DropdownMenu.Content align="end" sideOffset={16} class="w-48">
					<DropdownMenu.Label class="truncate font-medium text-foreground">
						@{user.username}
					</DropdownMenu.Label>
					<DropdownMenu.Separator />
					<DropdownMenu.Item onSelect={() => goto(resolve('/profile'))}>
						<User aria-hidden="true" />
						Профиль
					</DropdownMenu.Item>
					<DropdownMenu.Item onSelect={handleLogout}>
						<LogOut aria-hidden="true" />
						Выйти
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{:else}
			<Button href="/login" size="sm">Войти</Button>
		{/if}
	</div>
</header>
