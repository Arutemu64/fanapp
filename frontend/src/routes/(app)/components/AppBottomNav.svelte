<script lang="ts">
	import { BottomNav, BottomNavItem } from 'flowbite-svelte';
	import {
		CalendarWeekOutline,
		HomeSolid,
		MapPinAltOutline,
		ThumbsUpOutline
	} from 'flowbite-svelte-icons';

	let { activeUrl } = $props<{ activeUrl: string }>();
</script>

<BottomNav
	{activeUrl}
	position="fixed"
	class="bottom-0 left-0 z-50 w-full border-t border-gray-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden dark:border-gray-800 dark:bg-gray-900"
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
	<!-- Mirror the sidebar shortcut here so the map stays visible above the fixed mobile nav. -->
	<BottomNavItem btnName="Карта" href="/map">
		<MapPinAltOutline
			class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
		/>
	</BottomNavItem>
	<BottomNavItem btnName="Голосование" href="/voting">
		<ThumbsUpOutline
			class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-500"
		/>
	</BottomNavItem>
</BottomNav>
