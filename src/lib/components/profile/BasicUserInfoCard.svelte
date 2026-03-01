<script lang="ts">
	import { Avatar, Badge, Card, Button } from 'flowbite-svelte';
	import { TicketSolid } from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { getRoleLabel, getRoleColor } from '$lib/utils/users';
	import EditProfileModal from './EditProfileModal.svelte';

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();

	let editProfileModalOpen = $state(false);
</script>

<Card class="w-full max-w-none rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="flex flex-col gap-4">
			<div class="flex items-center gap-4">
				<Avatar size="lg" />

				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
						<h3 class="text-lg font-bold text-gray-900 dark:text-white">
							{user.first_name || 'Пользователь'}
						</h3>
						<Badge color={getRoleColor(user.role)} class="text-sm">
							{getRoleLabel(user.role)}
						</Badge>
					</div>

					{#if user.username}
						<p class="text-sm text-gray-500 dark:text-gray-400">@{user.username}</p>
					{/if}

					<div class="mt-2 space-y-1">
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

			<div class="mt-2 text-center">
				<Button
					color="alternative"
					size="sm"
					class="w-full sm:w-auto"
					onclick={() => (editProfileModalOpen = true)}
				>
					Редактировать
				</Button>
			</div>
		</div>
	</div>
</Card>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
