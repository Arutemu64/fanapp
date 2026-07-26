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

<!-- A primary destination. `aria-current` is what tells a screen reader which tab
     you are on: the visual cue is a solid-vs-outline icon in a different colour,
     and neither shape nor colour reaches assistive tech. -->
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

<!-- Flowbite renders BottomNav as a plain <div>, so the app's primary mobile
     navigation would carry no landmark at all; the explicit role + label put it
     back in the landmark list next to the sidebar's own <nav>. -->
<BottomNav
	{activeUrl}
	position="fixed"
	role="navigation"
	aria-label="Основная навигация"
	class="bottom-0 left-0 z-50 w-full border-t border-gray-200 bg-white pr-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] pl-[env(safe-area-inset-left)] md:hidden dark:border-gray-700 dark:bg-gray-900"
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
