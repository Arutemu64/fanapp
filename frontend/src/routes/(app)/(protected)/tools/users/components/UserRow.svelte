<script lang="ts">
	import { resolve } from '$app/paths';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	import type { UserListItemDto } from '#lib/api/generated/index.js';

	import { Badge } from '#lib/components/ui/badge/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	interface Props {
		user: UserListItemDto;
	}

	let { user }: Props = $props();

	let details = $derived(user.ticket_number ?? user.email ?? m.user_row_no_contacts());
</script>

<a
	href={resolve(`tools/users/${user.id}`)}
	class="flex min-h-16 items-center gap-3 px-3 py-2.5 transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset sm:px-4"
>
	<UserAvatar seed={user.avatar_seed} class="size-10" />
	<span class="flex min-w-0 flex-1 flex-col gap-0.5">
		<span class="flex min-w-0 items-center gap-2">
			<span class="min-w-0 text-sm font-medium wrap-anywhere text-foreground">{user.username}</span>
			<Badge variant="secondary" class="shrink-0">{getRoleLabel(user.role)}</Badge>
		</span>
		<span class={['truncate text-xs text-muted-foreground', user.ticket_number && 'font-mono']}>
			{details}
		</span>
	</span>
	<ChevronRight class="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
</a>
