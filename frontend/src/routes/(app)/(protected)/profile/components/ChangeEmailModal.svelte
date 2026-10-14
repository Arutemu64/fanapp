<script lang="ts">
	import { Mail } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ChangeEmailInput } from '#lib/api/generated/index.js';

	import {
		changeCurrentUserEmailMutation,
		confirmEmailCodeMutation,
		getCurrentUserQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import ChangeEmailForm from './ChangeEmailForm.svelte';

	interface Props {
		open: boolean;
		currentEmail?: string | null;
	}

	let { open = $bindable(false), currentEmail }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The mutations live here, not in the form: the form unmounts when the dialog
	// closes and would take `isPending` with it, so a close and reopen mid-request
	// could send a second code email. `mutateAsync` so the form can await them for
	// its errors (ADR-0022).
	// Sends the code — first from the email step, then as «Отправить код ещё раз».
	const changeEmailMutation = createMutation(() => changeCurrentUserEmailMutation());
	// Not awaited: the refreshed user flips `currentEmail`, and with it this
	// dialog's title, so the dialog closes first.
	const confirmMutation = createMutation(() => ({
		...confirmEmailCodeMutation(),
		onSuccess: () => void queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));

	// Screen-reader description for the dialog (visually the form speaks for itself).
	let dialogDescription = $derived(currentEmail ? m.email_modal_change() : m.email_modal_add());

	async function sendCode(body: ChangeEmailInput) {
		await changeEmailMutation.mutateAsync({ body });
	}

	async function confirm(code: string) {
		await confirmMutation.mutateAsync({ body: { code } });
		toastService.add(m.email_confirmed(), 'success');
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Mail class="size-5 text-muted-foreground" />
				{currentEmail ? m.email_modal_title_change() : m.email_modal_title_add()}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{dialogDescription}</Dialog.Description>
		</Dialog.Header>

		<ChangeEmailForm
			{currentEmail}
			sending={changeEmailMutation.isPending}
			confirming={confirmMutation.isPending}
			onSendCode={sendCode}
			onConfirm={confirm}
		/>
	</Dialog.Content>
</Dialog.Root>
