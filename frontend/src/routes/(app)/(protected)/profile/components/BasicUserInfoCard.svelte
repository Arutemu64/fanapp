<script lang="ts">
	import { Avatar, Badge, Button, Card } from 'flowbite-svelte';
	import { PenSolid } from 'flowbite-svelte-icons';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { getRoleLabel, getRoleColor } from '$lib/utils/users';
	import EditProfileModal from './EditProfileModal.svelte';

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();
	// Build avatar initials from the username (two parts -> two letters), falling back to the first name.
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

<!--
	Identity banner. Deliberately NOT a ProfileCardShell: it skips the icon-chip header the
	settings cards share and leads with the avatar + name, so it reads as "who you are" and
	anchors the page above the settings group rather than looking like a fifth settings panel.
-->
<Card
	class="w-full max-w-none rounded-2xl border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
>
	<div class="flex items-center gap-4 p-5 sm:gap-5 sm:p-6">
		<Avatar size="xl" class="shrink-0">{avatarInitials}</Avatar>

		<div class="min-w-0 flex-1">
			<div class="flex items-start gap-2">
				<!-- Wrap (don't truncate) so the full handle stays visible; the 25-char cap fits in 2 lines. -->
				<h2 class="min-w-0 text-xl font-bold break-words text-gray-900 sm:text-2xl dark:text-white">
					@{user.username}
				</h2>
				<Button
					color="alternative"
					size="sm"
					class="min-h-11 min-w-11 shrink-0 !p-2"
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
</Card>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
