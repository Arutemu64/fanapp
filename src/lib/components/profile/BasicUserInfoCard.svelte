<script lang="ts">
	import { Avatar, Badge } from 'flowbite-svelte';
	import { TicketSolid, UserCircleSolid } from 'flowbite-svelte-icons';
	import type { UserFullDTO } from '$lib/types/user';
	import { getRoleLabel, getRoleColor } from '$lib/utils/users';

	interface Props {
		user: UserFullDTO;
	}

	let { user }: Props = $props();
</script>

<div class="flex items-center gap-4 rounded-lg bg-white p-4 shadow dark:bg-gray-800">
	<Avatar size="lg" />

	<div class="min-w-0 flex-1">
		<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
			<h2 class="text-lg font-bold text-gray-900 dark:text-white">
				{user.first_name || 'Пользователь'}
			</h2>
			<Badge color={getRoleColor(user.role)}>
				{getRoleLabel(user.role)}
			</Badge>
		</div>

		{#if user.username}
			<p class="text-sm text-gray-500 dark:text-gray-400">@{user.username}</p>
		{/if}

		<div class="mt-2 space-y-1">
			{#if user.tg_id}
				<div class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
					<UserCircleSolid class="h-4 w-4 text-gray-400" />
					<span>ID: {user.tg_id}</span>
				</div>
			{/if}
			<div class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
				<TicketSolid class="h-4 w-4 text-gray-400" />
				{#if user.ticket}
					<span>{user.ticket.barcode}</span>
				{:else}
					<span class="text-gray-400 dark:text-gray-500">не привязан</span>
				{/if}
			</div>
		</div>
	</div>
</div>
