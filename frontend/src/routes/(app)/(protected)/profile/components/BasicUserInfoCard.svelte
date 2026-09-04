<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import * as Avatar from '$lib/components/ui/avatar';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { getAvatarInitials, getRoleLabel } from '$lib/utils/users';
	import { Pencil } from '@lucide/svelte';

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
<Card.Root class="w-full max-w-none rounded-2xl">
	<!--
		Mobile: centered vertical stack (avatar / name / role / edit) so the full username gets
		the card's width and never clips. sm+: the horizontal banner — avatar left, name + role
		in the middle, edit action on the right.
	-->
	<!-- Horizontal padding only: Card.Root's py-(--card-spacing) owns the vertical. -->
	<div
		class="flex flex-col items-center gap-3 px-5 text-center sm:flex-row sm:gap-5 sm:px-6 sm:text-left"
	>
		<Avatar.Root class="size-16 shrink-0 text-xl font-bold">
			<Avatar.Fallback class="bg-primary/10 text-primary">
				{avatarInitials}
			</Avatar.Fallback>
		</Avatar.Root>

		<div class="flex min-w-0 flex-col items-center gap-2 sm:flex-1 sm:items-start">
			<h2 class="min-w-0 text-xl font-bold break-words text-foreground sm:text-2xl">
				@{user.username}
			</h2>
			<Badge variant="secondary" class="text-xs">
				{getRoleLabel(user.role)}
			</Badge>
		</div>

		<Button
			variant="outline"
			size="sm"
			class="min-h-11 shrink-0"
			disabled={offlineGate.disabled}
			title={offlineGate.title}
			onclick={() => (editProfileModalOpen = true)}
		>
			<Pencil data-icon="inline-start" />
			Редактировать
		</Button>
	</div>
</Card.Root>

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
