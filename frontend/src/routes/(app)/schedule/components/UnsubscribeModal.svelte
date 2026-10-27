<script lang="ts">
	import { ParaglideMessage } from '@inlang/paraglide-js-svelte';
	import Bell from '@lucide/svelte/icons/bell';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { MessageTagProps } from '#lib/types/markup.js';
	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import { handOffWhenQueued } from '#lib/api/queuedWrite.svelte.js';
	import { cancelQueuedSubscribe, queuedUnsubscribeOptions } from '#lib/api/writeQueue.js';
	import FormError from '#lib/components/FormError.svelte';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		open: boolean;
		event: ScheduleEventWithSubscription;
	}
	let { open = $bindable(), event }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const unsubscribeMutation = createMutation(() => queuedUnsubscribeOptions(event.id));
	handOffWhenQueued(unsubscribeMutation, () => {
		toastService.add(m.unsubscribe_queued(), 'info');
		open = false;
	});

	let formError = $state('');

	function handleUnsubscribe() {
		if (!event.user_subscription) {
			open = false;
			return;
		}

		if (event.user_subscription.id === null) {
			if (cancelQueuedSubscribe(queryClient, event.id)) {
				toastService.add(m.unsubscribe_done(), 'success');
				open = false;
			} else {
				formError = m.subscribe_still_sending();
			}
			return;
		}

		formError = '';
		unsubscribeMutation.mutate(
			{ path: { subscription_id: event.user_subscription.id } },
			{
				onSuccess: () => {
					toastService.add(m.unsubscribe_done(), 'success');
					open = false;
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? m.unsubscribe_failed();
				}
			}
		);
	}
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<Bell class="size-5 text-muted-foreground" />
				{m.unsubscribe_title()}
			</AlertDialog.Title>
			<AlertDialog.Description>
				<ParaglideMessage message={m.unsubscribe_confirm} inputs={{ title: event.title }}>
					{#snippet eventName({ children }: MessageTagProps)}
						<strong class="text-foreground">{@render children?.()}</strong>
					{/snippet}
				</ParaglideMessage>
			</AlertDialog.Description>
		</AlertDialog.Header>

		<FormError message={formError} />

		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<Button
				type="button"
				variant="destructive"
				onclick={handleUnsubscribe}
				disabled={unsubscribeMutation.isPending}>{m.common_unsubscribe()}</Button
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
