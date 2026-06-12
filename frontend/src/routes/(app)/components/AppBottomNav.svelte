<script lang="ts">
	import { Avatar, BottomNav, BottomNavItem } from 'flowbite-svelte';
	import {
		ArrowRightToBracketOutline,
		CalendarWeekOutline,
		CalendarWeekSolid,
		HomeOutline,
		HomeSolid,
		MapPinAltOutline,
		MapPinAltSolid,
		ThumbsUpOutline,
		ThumbsUpSolid
	} from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';

	let { activeUrl, user } = $props<{
		activeUrl: string;
		user: CurrentUserDTO | null;
	}>();

	function isActive(href: string): boolean {
		if (href === '/') return activeUrl === '/';
		return activeUrl === href || activeUrl.startsWith(href + '/');
	}

	// Initials shown inside the dock avatar; falls back to "П" (Пользователь).
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
</script>

<BottomNav
	{activeUrl}
	position="fixed"
	class="bottom-0 left-0 z-50 w-full border-t border-gray-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden dark:border-gray-800 dark:bg-gray-900"
	classes={{ inner: 'grid-cols-5' }}
>
	<BottomNavItem btnName="Главная" href="/">
		{#if isActive('/')}
			<HomeSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-500" />
		{:else}
			<HomeOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		{/if}
	</BottomNavItem>
	<BottomNavItem btnName="Расписание" href="/schedule">
		{#if isActive('/schedule')}
			<CalendarWeekSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-500" />
		{:else}
			<CalendarWeekOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		{/if}
	</BottomNavItem>
	<!-- Mirror the sidebar shortcut here so the map stays visible above the fixed mobile nav. -->
	<BottomNavItem btnName="Карта" href="/map">
		{#if isActive('/map')}
			<MapPinAltSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-500" />
		{:else}
			<MapPinAltOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		{/if}
	</BottomNavItem>
	<BottomNavItem btnName="Голосование" href="/voting">
		{#if isActive('/voting')}
			<ThumbsUpSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-500" />
		{:else}
			<ThumbsUpOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
			/>
		{/if}
	</BottomNavItem>
	<!-- Profile lives in the dock for logged-in users; logged-out users get a login
		shortcut in the same slot so the auth entry point stays reachable on mobile. -->
	{#if user}
		<BottomNavItem btnName="Профиль" href="/profile">
			<Avatar
				size="xs"
				class="mb-1 h-6 w-6 text-xs {isActive('/profile')
					? 'ring-2 ring-primary-600 dark:ring-primary-500'
					: ''}">{avatarInitials}</Avatar
			>
		</BottomNavItem>
	{:else}
		<BottomNavItem btnName="Войти" href="/login">
			<ArrowRightToBracketOutline
				class="mb-1 h-6 w-6 {isActive('/login')
					? 'text-primary-600 dark:text-primary-500'
					: 'text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500'}"
			/>
		</BottomNavItem>
	{/if}
</BottomNav>
