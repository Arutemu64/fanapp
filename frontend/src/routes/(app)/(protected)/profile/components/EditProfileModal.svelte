<script lang="ts">
	import { User } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { CurrentUserDto, UpdateCurrentUserInput } from '#lib/api/generated/index.js';

	import {
		getCurrentUserQueryKey,
		updateCurrentUserMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	import EditProfileForm from './EditProfileForm.svelte';

	interface Props {
		user: CurrentUserDto;
		open: boolean;
	}

	let { user, open = $bindable(false) }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const updateProfileMutation = createMutation(() => ({
		...updateCurrentUserMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));

	// The mutation lives here, not in the form: the form unmounts when the dialog
	// closes and would take `isPending` with it, so a close and reopen mid-request
	// could submit twice. `mutateAsync` so the form can await it for its errors
	// (ADR-0022).
	async function save(body: UpdateCurrentUserInput) {
		await updateProfileMutation.mutateAsync({ body });
		toastService.add(m.profile_updated(), 'success');
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<User class="size-5 text-muted-foreground" />
				{m.profile_edit_title()}
			</Dialog.Title>
			<Dialog.Description class="sr-only">{m.profile_edit_description()}</Dialog.Description>
		</Dialog.Header>

		<EditProfileForm
			{user}
			pending={updateProfileMutation.isPending}
			onSave={save}
			onClose={() => (open = false)}
		/>
	</Dialog.Content>
</Dialog.Root>
