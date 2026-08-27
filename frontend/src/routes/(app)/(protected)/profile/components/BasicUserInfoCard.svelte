<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { getAvatarInitials, getRoleColor, getRoleLabel } from '$lib/utils/users';
	import { Avatar, Badge, Button, Card } from 'flowbite-svelte';
	import { PenSolid } from 'flowbite-svelte-icons';

	import EditProfileModal from './EditProfileModal.svelte';

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();
	let avatarInitials = $derived(getAvatarInitials(user.username));

	// Editing the profile is a mutation — online only. Cached identity still renders.
	const offlineGate = offlineWriteGate();

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
	<!--
		Mobile: centered vertical stack (avatar / name / role / edit) so the full username gets
		the card's width and never clips. sm+: the horizontal banner — avatar left, name + role
		in the middle, edit action on the right.
	-->
	<div
		class="flex flex-col items-center gap-3 p-5 text-center sm:flex-row sm:gap-5 sm:p-6 sm:text-left"
	>
		<Avatar size="lg" class="shrink-0">{avatarInitials}</Avatar>

		<div class="flex min-w-0 flex-col items-center gap-2 sm:flex-1 sm:items-start">
			<h2 class="min-w-0 text-xl font-bold break-words text-gray-900 sm:text-2xl dark:text-white">
				@{user.username}
			</h2>
			<Badge color={getRoleColor(user.role)} border class="text-xs">
				{getRoleLabel(user.role)}
			</Badge>
		</div>

		<Button
			color="alternative"
			size="sm"
			class="min-h-11 shrink-0"
			disabled={offlineGate.disabled}
			title={offlineGate.title}
			onclick={() => (editProfileModalOpen = true)}
		>
			<PenSolid class="me-2 h-4 w-4" />
			Редактировать
		</Button>
	</div>
</Card>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
