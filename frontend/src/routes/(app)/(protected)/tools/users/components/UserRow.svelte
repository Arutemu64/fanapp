<script lang="ts">
	import { resolve } from '$app/paths';
	import { ChevronRight } from '@lucide/svelte';

	import type { UserListItemDto } from '#lib/api/generated/index.js';

	import { Badge } from '#lib/components/ui/badge/index.js';
	import { getAvatarInitials, getRoleLabel } from '#lib/utils/users.js';

	interface Props {
		user: UserListItemDto;
	}

	let { user }: Props = $props();

	// The ticket number is what staff check at the door, so it leads the second
	// line; the email fills in for someone without a ticket.
	let details = $derived(user.ticket_number ?? user.email ?? 'Нет билета и почты');
</script>

<!-- The whole row is one link, so the tap target is the full width rather than
     the username alone. -->
<a
	href={resolve(`tools/users/${user.id}`)}
	class="flex min-h-16 items-center gap-3 px-3 py-2.5 transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none sm:px-4"
>
	<span
		class="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary"
		aria-hidden="true"
	>
		{getAvatarInitials(user.username)}
	</span>
	<span class="flex min-w-0 flex-1 flex-col gap-0.5">
		<span class="flex min-w-0 items-center gap-2">
			<span class="truncate text-sm font-medium text-foreground">{user.username}</span>
			<Badge variant="secondary" class="shrink-0">{getRoleLabel(user.role)}</Badge>
		</span>
		<span class={['truncate text-xs text-muted-foreground', user.ticket_number && 'font-mono']}>
			{details}
		</span>
	</span>
	<ChevronRight class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
</a>
