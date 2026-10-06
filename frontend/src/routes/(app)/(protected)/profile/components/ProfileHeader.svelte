<script lang="ts">
	import type { CurrentUserDto } from '$lib/api/generated';

	import * as Avatar from '$lib/components/ui/avatar';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { getAvatarInitials, getRoleLabel } from '$lib/utils/users';
	import { Pencil } from '@lucide/svelte';

	import EditProfileModal from './EditProfileModal.svelte';

	interface Props {
		user: CurrentUserDto;
		onUpdate?: () => void;
	}

	let { user, onUpdate }: Props = $props();
	let avatarInitials = $derived(getAvatarInitials(user.username));

	// Editing the profile is a mutation — online only. Cached identity still renders.
	const offlineGate = offlineWriteGate();

	let editProfileModalOpen = $state(false);
</script>

<!--
	Identity header. Deliberately not a SettingsSection: it leads with the avatar + name, so it
	reads as "who you are" and anchors the page above the sign-in settings rather than looking
	like another settings group. No Card either — a frame around one line of identity groups
	nothing.
-->
<!--
	Mobile: centered vertical stack (avatar / name / role / edit) so the full username gets
	the page's width and never clips. sm+: the horizontal banner — avatar left, name + role
	in the middle, edit action on the right.
-->
<div class="flex flex-col items-center gap-3 text-center sm:flex-row sm:gap-5 sm:text-left">
	<Avatar.Root class="size-16 shrink-0 text-xl font-bold">
		<!-- primary-700 in light, as on the hub's account row: on the primary/10 tint it
		     measures 5.8:1, where primary-600 is 4.4:1, under AA's 4.5:1 for body text. -->
		<Avatar.Fallback class="bg-primary/10 text-primary-700 dark:text-primary">
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

<EditProfileModal {user} bind:open={editProfileModalOpen} {onUpdate} />
