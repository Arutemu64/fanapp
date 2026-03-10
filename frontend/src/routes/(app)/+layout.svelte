<script lang="ts">
	import AppShell from '$lib/components/layout/AppShell.svelte';
	import { canManageSchedule } from '$lib/utils/permissions';
	import {
		CalendarWeekOutline,
		ClockArrowOutline,
		HomeSolid,
		ThumbsUpOutline
	} from 'flowbite-svelte-icons';

	let { data, children } = $props();

	// Build app sidebar links in a layout dedicated to user-facing pages.
	let sidebarItems = $derived.by(() => {
		const items = [
			{ label: 'Главная', href: '/', icon: HomeSolid },
			{ label: 'Расписание', href: '/schedule', icon: CalendarWeekOutline },
			{ label: 'Голосование', href: '/voting', icon: ThumbsUpOutline }
		];

		if (canManageSchedule(data.user)) {
			items.push({
				label: 'Изменения расписания',
				href: '/schedule/changes',
				icon: ClockArrowOutline
			});
		}

		return items;
	});

	const bottomNavItems = [
		{ label: 'Главная', href: '/', icon: HomeSolid },
		{ label: 'Расписание', href: '/schedule', icon: CalendarWeekOutline },
		{ label: 'Голосование', href: '/voting', icon: ThumbsUpOutline }
	];
</script>

<AppShell
	{data}
	{children}
	{sidebarItems}
	{bottomNavItems}
	showBottomNav={true}
	contentBottomPaddingClass="pb-24"
/>
