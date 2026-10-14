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
			toastService.add(
				'Билет отвязан, голоса удалены. Роль не менялась — если нужно, смени её вручную.',
				'success'
			);
			return Promise.all([
				queryClient.invalidateQueries({ queryKey: getUserQueryKey({ path: { user_id: userId } }) }),
				queryClient.invalidateQueries({ queryKey: listUsersQueryKey() })
			]);
		},
		onError: (error) => toastService.error(error, 'Не удалось отвязать билет')
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
