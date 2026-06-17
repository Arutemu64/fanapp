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
	let avatarInitials = $derived.by(() => {
		const username = user.username?.trim().replace(/^@/, '');

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

	let editProfileModalOpen = $state(false);
</script>

<ProfileCardShell title="Основные данные" description="Всё о тебе.">
	{#snippet icon()}
		<UserCircleSolid class="h-5 w-5" />
	{/snippet}

	<div class="flex min-w-0 items-center gap-4">
		<Avatar size="lg">{avatarInitials}</Avatar>

		<div class="min-w-0">
			<div class="flex items-center gap-2">
				<h4 class="truncate text-lg font-semibold text-gray-900 dark:text-white">
					@{user.username}
				</h4>
				<Button
					color="alternative"
					size="sm"
					class="min-h-9 shrink-0 !p-2"
					aria-label="Редактировать псевдоним"
					onclick={() => (editProfileModalOpen = true)}
				>
					<PenSolid class="h-4 w-4" />
				</Button>
			</div>

			<div class="mt-2">
				<Badge color={getRoleColor(user.role)} border class="text-xs">
					{getRoleLabel(user.role)}
				</Badge>
			</div>
		</div>
	</div>
</ProfileCardShell>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
