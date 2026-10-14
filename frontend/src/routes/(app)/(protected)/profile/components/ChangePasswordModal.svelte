<script lang="ts">
	import { Lock } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ChangePasswordInput } from '#lib/api/generated/index.js';

	import {
		changeCurrentUserPasswordMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import ChangePasswordForm from './ChangePasswordForm.svelte';

	interface Props {
		open: boolean;
		hasPassword?: boolean;
	}

	let { open = $bindable(false), hasPassword = true }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// Not awaited: the refreshed user flips `hasPassword`, and with it this
	// dialog's title and toast, so the dialog closes first.
	const changePasswordMutation = createMutation(() => ({
		...changeCurrentUserPasswordMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));

	// Screen-reader description for the dialog (visually the form speaks for itself).
	let dialogDescription = $derived(
		hasPassword ? 'Смени пароль от своего аккаунта.' : 'Задай пароль для входа в аккаунт.'
	);

	// The mutation lives here, not in the form: the form unmounts when the dialog
	// closes and would take `isPending` with it, so a close and reopen mid-request
	// could submit twice. `mutateAsync` so the form can await it for its errors
	// (ADR-0022).
	async function save(body: ChangePasswordInput) {
		await changePasswordMutation.mutateAsync({ body });
		toastService.add(hasPassword ? 'Пароль изменён' : 'Пароль установлен', 'success');
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Lock class="size-5 text-muted-foreground" />
				{hasPassword ? 'Изменение пароля' : 'Установка пароля'}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
		</Dialog.Header>

		<ChangePasswordForm {hasPassword} pending={changePasswordMutation.isPending} onSave={save} />
	</Dialog.Content>
</Dialog.Root>
