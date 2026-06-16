<script lang="ts">
	import { Avatar, Badge, Button } from 'flowbite-svelte';
	import { PenSolid, UserCircleSolid } from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { getRoleLabel, getRoleColor } from '$lib/utils/users';
	import EditProfileModal from './EditProfileModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();
	// Build avatar initials from the username (two parts -> two letters), falling back to the first name.
	let avatarInitials = $derived.by(() => {
		const rawUsername = user.username?.trim();

		if (!rawUsername) {
			return (user.first_name?.trim()?.[0] || 'П').toUpperCase();
		}

		const username = rawUsername.replace(/^@/, '');

		if (!username) {
			return (user.first_name?.trim()?.[0] || 'П').toUpperCase();
		}

		const parts = username.split(/[\s._-]+/).filter(Boolean);

		if (parts.length >= 2) {
			const firstInitial = parts[0]?.[0] ?? '';
			const secondInitial = parts[1]?.[0] ?? '';

			return `${firstInitial}${secondInitial}`.toUpperCase();
		}

		return username.slice(0, 2).toUpperCase();
	});

	let editProfileModalOpen = $state(false);
</script>

<ProfileCardShell title="Основные данные" description="Всё о тебе.">
	{#snippet icon()}
		<UserCircleSolid class="h-5 w-5" />
	{/snippet}

	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div class="flex min-w-0 items-center gap-4">
			<Avatar size="lg">{avatarInitials}</Avatar>

			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<h4 class="truncate text-lg font-semibold text-gray-900 dark:text-white">
						{user.first_name || 'Пользователь'}
					</h4>
					<Badge color={getRoleColor(user.role)} border class="text-xs">
						{getRoleLabel(user.role)}
					</Badge>
				</div>

				{#if user.username}
					<p class="mt-1 truncate text-sm text-gray-500 dark:text-gray-400">@{user.username}</p>
				{/if}
			</div>
		</div>

		<Button
			color="alternative"
			size="sm"
			class="min-h-11 w-full shrink-0 sm:w-auto"
			onclick={() => (editProfileModalOpen = true)}
		>
			<PenSolid class="me-2 h-4 w-4" />
			Редактировать профиль
		</Button>
	</div>
</ProfileCardShell>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
