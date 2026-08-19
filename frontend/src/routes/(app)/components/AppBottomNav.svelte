<script lang="ts">
	import type { Component } from 'svelte';

	import { isActivePath } from '$lib/utils/nav';
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

	interface Props {
		activeUrl: string;
	}

	let { activeUrl }: Props = $props();
</script>

{#snippet navItem(label: string, href: string, OutlineIcon: Component, SolidIcon: Component)}
	{@const active = isActivePath(activeUrl, href)}
	<BottomNavItem btnName={label} {href} aria-current={active ? 'page' : undefined}>
		{#if active}
			<SolidIcon class="mb-1 h-6 w-6 text-primary-600 dark:text-primary-400" />
		{:else}
			<OutlineIcon
				class="mb-1 h-6 w-6 text-gray-500 group-hover:text-primary-600 dark:text-gray-400 dark:group-hover:text-primary-400"
			/>
		{/if}
	</BottomNavItem>
{/snippet}

<!-- BottomNav renders a plain <div>, so the bar is no landmark until `role` names it. The
     label omits "навигация" — the role is announced already — and matches the desktop
     sidebar's: same navigation at the opposite breakpoint, never in the tree together. -->
<BottomNav
	{activeUrl}
	position="fixed"
	role="navigation"
	aria-label="Разделы"
	class="z-(--z-overlay) pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] md:hidden dark:border-gray-700 dark:bg-gray-900"
	classes={{ inner: 'grid-cols-4' }}
>
	{@render navItem('Главная', '/', HomeOutline, HomeSolid)}
	{@render navItem('Программа', '/schedule', CalendarWeekOutline, CalendarWeekSolid)}
	<!-- Voting sits before the map so its long "Голосование" label lands in an inner
	     column, away from rounded screen corners that clip the edge items. -->
	{@render navItem('Голосование', '/voting', ThumbsUpOutline, ThumbsUpSolid)}
	<!-- Mirror the sidebar shortcut here so the map stays visible above the fixed mobile nav. -->
	{@render navItem('Карта', '/map', MapPinAltOutline, MapPinAltSolid)}
</BottomNav>
