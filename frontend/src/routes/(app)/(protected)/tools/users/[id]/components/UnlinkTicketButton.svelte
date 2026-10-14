<script lang="ts">
	import { Unlink } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import { getApiErrorCode } from '#lib/api/errors.js';
	import {
		getUserQueryKey,
		listUsersQueryKey,
		unlinkUserTicketMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { pluralize } from '#lib/utils/formatters.js';

	interface Props {
		userId: string;
		username: string;
	}

	let { userId, username }: Props = $props();

	const queryClient = useQueryClient();
	const toastService = getToastService();
	let confirmOpen = $state(false);

	// The role is deliberately left alone by the backend, so the toast says so:
	// the organiser decides whether it should go with the ticket.
	const ROLE_HINT = 'Роль не менялась — если нужно, смени её вручную.';

	function invalidateUser() {
		return Promise.all([
			queryClient.invalidateQueries({ queryKey: getUserQueryKey({ path: { user_id: userId } }) }),
			queryClient.invalidateQueries({ queryKey: listUsersQueryKey() })
		]);
	}

	// Toasts sit on the mutation, not on the mutate() call: the refetch drops the
	// ticket and with it this button, and call-level callbacks are skipped once
	// their component has unmounted (docs/api.md).
	const unlinkMutation = createMutation(() => ({
		...unlinkUserTicketMutation(),
		onSuccess: ({ deleted_votes: deleted }) => {
			let message = 'Билет отвязан.';
			if (deleted > 0) {
				const votes = pluralize(deleted, 'голос', 'голоса', 'голосов');
				message = `Билет отвязан, удалено ${deleted} ${votes}.`;
			}
			toastService.add(`${message} ${ROLE_HINT}`, 'success');
			return invalidateUser();
		},
		onError: (error) => {
			// The shared copy for this code speaks to the ticket's owner.
			if (getApiErrorCode(error) === 'TICKET_NOT_LINKED') {
				toastService.add('У пользователя уже нет билета', 'error');
				return invalidateUser();
			}
			toastService.error(error, 'Не удалось отвязать билет');
		}
	}));
</script>

<Button
	variant="outline"
	class="w-full sm:w-auto"
	disabled={unlinkMutation.isPending}
	onclick={() => (confirmOpen = true)}
>
	<Unlink data-icon="inline-start" />
	Отвязать билет
</Button>

<!-- AlertDialog per the confirmation convention (docs/frontend.md §7): Cancel comes
     first so the safe choice takes focus. -->
<AlertDialog.Root bind:open={confirmOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>Отвязать билет?</AlertDialog.Title>
			<AlertDialog.Description>
				Голоса {username} удалятся. Роль останется прежней — если нужно, смени её вручную. Билет можно
				будет привязать снова.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<AlertDialog.Action
				variant="destructive"
				onclick={() => unlinkMutation.mutate({ path: { user_id: userId } })}
				>Отвязать</AlertDialog.Action
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
