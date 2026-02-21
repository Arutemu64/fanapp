<script lang="ts">
	import { eventsClient } from '$lib/events.svelte';
	import type { FullUserDTO } from '$lib/types/user';
	import {
		DarkMode,
		Avatar,
		Dropdown,
		DropdownHeader,
		DropdownGroup,
		DropdownItem,
		Navbar,
		NavBrand
	} from 'flowbite-svelte';

	interface Props {
		user: FullUserDTO | null;
	}

	let { user }: Props = $props();
</script>

<Navbar
	id="top-navbar"
	class="sticky top-0 z-30 border-b border-gray-200 bg-white px-4 py-2.5 sm:px-6 dark:border-gray-700 dark:bg-gray-900"
>
	<NavBrand href="/">
		<span class="self-center text-xl font-semibold whitespace-nowrap dark:text-white">
			FAN App
		</span>
	</NavBrand>
	<div class="flex items-center gap-2 md:order-2">
		<DarkMode id="dark-mode-toggle" />
		{#if user}
			<Avatar
				id="avatar-menu"
				dot={{
					placement: 'bottom-right',
					color:
						eventsClient.connectionStatus === 'connected'
							? 'green'
							: eventsClient.connectionStatus === 'connecting'
								? 'yellow'
								: 'red'
				}}
			/>
		{/if}
	</div>
	{#if user}
		<Dropdown placement="bottom" triggeredBy="#avatar-menu">
			<DropdownHeader>
				<span class="block text-sm">{user.first_name}</span>
				<span class="block truncate text-sm font-medium">@{user.username}</span>
			</DropdownHeader>
			<DropdownGroup>
				<DropdownItem href="/link_ticket">Привязать билет</DropdownItem>
				<DropdownItem>Настройки</DropdownItem>
			</DropdownGroup>
			<DropdownItem>Выйти</DropdownItem>
		</Dropdown>
	{/if}
</Navbar>
