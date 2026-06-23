<script lang="ts">
	import { BottomNav, BottomNavItem } from 'flowbite-svelte';
	import {
		CalendarWeekOutline,
		CalendarWeekSolid,
		HomeOutline,
		HomeSolid,
		MapPinAltOutline,
		MapPinAltSolid,
		ThumbsUpOutline,
		ThumbsUpSolid
	} from 'flowbite-svelte-icons';

	let { activeUrl } = $props<{ activeUrl: string }>();

	function isActive(href: string): boolean {
		if (href === '/') return activeUrl === '/';
		return activeUrl === href || activeUrl.startsWith(href + '/');
	}
</script>

<BottomNav
	{activeUrl}
	position="fixed"
	class="bottom-0 left-0 z-50 w-full border-t border-gray-200 bg-white pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] md:hidden dark:border-gray-700 dark:bg-gray-900"
	classes={{ inner: 'grid-cols-4' }}
>
	<BottomNavItem btnName="Главная" href="/">
		{#if isActive('/')}
			<HomeSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
		{:else}
			<HomeOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
			/>
		{/if}
	</BottomNavItem>
	<BottomNavItem btnName="Расписание" href="/schedule">
		{#if isActive('/schedule')}
			<CalendarWeekSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
		{:else}
			<CalendarWeekOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
			/>
		{/if}
	</BottomNavItem>
	<!-- Voting sits before the map so its long "Голосование" label lands in an inner
	     column, away from rounded screen corners that clip the edge items. -->
	<BottomNavItem btnName="Голосование" href="/voting">
		{#if isActive('/voting')}
			<ThumbsUpSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
		{:else}
			<ThumbsUpOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
			/>
		{/if}
	</BottomNavItem>
	<!-- Mirror the sidebar shortcut here so the map stays visible above the fixed mobile nav. -->
	<BottomNavItem btnName="Карта" href="/map">
		{#if isActive('/map')}
			<MapPinAltSolid class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
		{:else}
			<MapPinAltOutline
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
			/>
		{/if}
	</BottomNavItem>
</BottomNav>
