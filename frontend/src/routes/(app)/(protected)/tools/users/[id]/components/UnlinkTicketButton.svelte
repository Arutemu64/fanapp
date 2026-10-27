<script lang="ts">
	import Unlink from '@lucide/svelte/icons/unlink';
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

	const unlinkMutation = createMutation(() => ({
		...unlinkUserTicketMutation(),
		onSuccess: () => {
			toastService.add(m.ticket_unlinked_toast(), 'success');
			return Promise.all([
				queryClient.invalidateQueries({ queryKey: getUserQueryKey({ path: { user_id: userId } }) }),
				queryClient.invalidateQueries({ queryKey: listUsersQueryKey() })
			]);
		},
		onError: (error) => toastService.error(error, m.ticket_unlink_failed())
	}));
</script>

<Button
	variant="outline"
	class="w-full sm:w-auto"
	disabled={unlinkMutation.isPending}
	onclick={() => (confirmOpen = true)}
>
	<Unlink data-icon="inline-start" />
	{m.ticket_unlink_action()}
</Button>

<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.ticket_unlink_confirm_title()}</AlertDialog.Title>
			<AlertDialog.Description>
				{m.ticket_unlink_confirm_description({ username })}
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action
				variant="destructive"
				onclick={() => unlinkMutation.mutate({ path: { user_id: userId } })}
				>{m.common_unlink()}</AlertDialog.Action
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
