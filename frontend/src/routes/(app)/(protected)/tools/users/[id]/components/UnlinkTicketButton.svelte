<script lang="ts">
	import { Unlink } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import {
		getUserQueryKey,
		listUsersQueryKey,
		unlinkUserTicketMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		userId: string;
		username: string;
	}

	let { userId, username }: Props = $props();

	const queryClient = useQueryClient();
	const toastService = getToastService();
	let confirmOpen = $state(false);

	// Toasts sit on the mutation, not on the mutate() call: the refetch drops the
	// ticket and with it this button, and call-level callbacks are skipped once
	// their component has unmounted (docs/api.md).
	const unlinkMutation = createMutation(() => ({
		...unlinkUserTicketMutation(),
		onSuccess: () => {
			// The backend leaves the role alone, so the organiser is told to change it.
			toastService.add(m.user_unlink_done(), 'success');
			return Promise.all([
				queryClient.invalidateQueries({ queryKey: getUserQueryKey({ path: { user_id: userId } }) }),
				queryClient.invalidateQueries({ queryKey: listUsersQueryKey() })
			]);
		},
		onError: (error) => toastService.error(error, m.user_unlink_failed())
	}));
</script>

<Button
	variant="outline"
	class="w-full sm:w-auto"
	disabled={unlinkMutation.isPending}
	onclick={() => (confirmOpen = true)}
>
	<Unlink data-icon="inline-start" />
	{m.user_unlink_ticket()}
</Button>

<!-- AlertDialog per the confirmation convention (docs/frontend.md §7): Cancel comes
     first so the safe choice takes focus. -->
<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.user_unlink_title()}</AlertDialog.Title>
			<AlertDialog.Description>
				{m.user_unlink_description({ username })}
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action
				variant="destructive"
				onclick={() => unlinkMutation.mutate({ path: { user_id: userId } })}
				>{m.social_unlink()}</AlertDialog.Action
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
