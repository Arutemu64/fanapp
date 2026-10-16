<script lang="ts">
	import { Pencil } from '@lucide/svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	import EditProfileModal from './EditProfileModal.svelte';

	interface Props {
		user: CurrentUserDto;
	}

	let { user }: Props = $props();

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
	<UserAvatar seed={user.avatar_seed} class="size-16" />

	<div class="flex min-w-0 flex-col items-center gap-2 sm:flex-1 sm:items-start">
		<h2 class="min-w-0 text-headline break-words text-foreground">
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
		aria-disabled={offlineGate.blocked}
		onclick={offlineGate.guard(() => (editProfileModalOpen = true))}
	>
		<Pencil data-icon="inline-start" />
		{m.profile_edit_action()}
	</Button>
</div>

<EditProfileModal {user} bind:open={editProfileModalOpen} />
