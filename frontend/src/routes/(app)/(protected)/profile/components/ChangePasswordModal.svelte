<script lang="ts">
	import { Lock } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ChangePasswordInput } from '#lib/api/generated/index.js';

	import {
		changeCurrentUserPasswordMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import ChangePasswordForm from './ChangePasswordForm.svelte';

	interface Props {
		open: boolean;
		hasPassword?: boolean;
		// Account email, handed to password managers as the username of the password
		// being saved. Null for an account that signs in through a social service.
		email?: string | null;
	}

	let { open = $bindable(false), hasPassword = true, email = null }: Props = $props();
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
		hasPassword ? m.password_modal_description_change() : m.password_modal_description_set()
	);

	// The mutation lives here, not in the form: the form unmounts when the dialog
	// closes and would take `isPending` with it, so a close and reopen mid-request
	// could submit twice. `mutateAsync` so the form can await it for its errors
	// (ADR-0022).
	async function save(body: ChangePasswordInput) {
		await changePasswordMutation.mutateAsync({ body });
		toastService.add(hasPassword ? m.password_changed() : m.password_set_done(), 'success');
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Lock class="size-5 text-muted-foreground" />
				{hasPassword ? m.password_modal_title_change() : m.password_modal_title_set()}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
		</Dialog.Header>

		<ChangePasswordForm
			{hasPassword}
			{email}
			pending={changePasswordMutation.isPending}
			onSave={save}
		/>
	</Dialog.Content>
</Dialog.Root>
