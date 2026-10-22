<script lang="ts">
	import { resolve } from '$app/paths';
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';
	import type { MessageTagProps } from '#lib/types/markup.js';

	import {
		getCurrentUserQueryKey,
		updateCurrentUserSettingsMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SwitchRow from '#lib/components/SwitchRow.svelte';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	interface Props {
		open: boolean;
		user: CurrentUserDto;
	}

	let { open = $bindable(), user }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const settingsMutation = createMutation(() => ({
		...updateCurrentUserSettingsMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() })
	}));
	// A settings PATCH: online only. The current state still renders.
	const offlineGate = offlineWriteGate();

	// Writable derived: the toggle overrides it optimistically, and it snaps back to
	// the server copy whenever `user` refreshes (Svelte "Overriding derived values").
	let receiveAll = $derived(user.settings.receive_all_announcements);

	function toggleReceiveAll(checked: boolean) {
		receiveAll = checked;
		// No success toast: the switch already sits in its new position, and a
		// switch is expected to take effect on its own
		// (https://www.nngroup.com/articles/toggle-switch-guidelines/).
		settingsMutation.mutate(
			{ body: { receive_all_announcements: checked } },
			{
				onError: () => {
					toastService.add(m.push_settings_update_failed(), 'error');
					receiveAll = user.settings.receive_all_announcements;
				}
			}
		);
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>{m.schedule_notifications_title()}</Dialog.Title>
		</Dialog.Header>

		<MenuGroup>
			<SwitchRow
				id="all-announcements"
				title={m.push_all_announcements_title()}
				description={m.push_all_announcements_description()}
				checked={receiveAll}
				disabled={settingsMutation.isPending}
				blocked={offlineGate.blocked}
				onCheckedChange={offlineGate.guard(toggleReceiveAll)}
			/>
		</MenuGroup>

		<!-- The switch only picks what is sent; whether it arrives depends on the channels,
		     which stay in the profile with the rest of the delivery setup. -->
		<p class="text-sm leading-relaxed text-muted-foreground">
			<ParaglideMessage message={m.schedule_notifications_channels}>
				{#snippet link({ children }: MessageTagProps)}
					<a
						href={resolve('profile/notifications')}
						class="font-medium text-primary hover:underline">{@render children?.()}</a
					>
				{/snippet}
			</ParaglideMessage>
		</p>
	</Dialog.Content>
</Dialog.Root>
