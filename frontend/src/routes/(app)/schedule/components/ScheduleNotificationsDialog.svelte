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
	const offlineGate = offlineWriteGate();

	let receiveAll = $derived(user.settings.receive_all_announcements);

	function toggleReceiveAll(checked: boolean) {
		receiveAll = checked;
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
