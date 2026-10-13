<script lang="ts">
	import { Bell } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		deleteSubscriptionMutation,
		getSubscriptionsQueryKey
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	interface Props {
		open: boolean;
		event: ScheduleEventWithSubscription;
	}
	let { open = $bindable(), event }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const unsubscribeMutation = createMutation(() => ({
		...deleteSubscriptionMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() })
	}));

	let formError = $state('');

	$effect(() => {
		if (open) {
			formError = '';
		}
	});

	function handleUnsubscribe() {
		if (!event.user_subscription) {
			open = false;
			return;
		}

		formError = '';
		unsubscribeMutation.mutate(
			{ path: { subscription_id: event.user_subscription.id } },
			{
				onSuccess: () => {
					toastService.add('Подписка на уведомления отключена', 'success');
					open = false;
				},
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось отключить уведомления';
				}
			}
		);
	}
</script>

<!-- AlertDialog (role="alertdialog"), not Dialog: a confirmation that must force an
	explicit choice and not dismiss on an outside click. The confirm is a plain Button
	(not AlertDialog.Action) because the request is fired here and a failure must keep
	the dialog open to show formError — Action would auto-close and drop the message. -->
<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title class="flex items-center gap-2">
				<Bell class="size-5 text-muted-foreground" />
				Отписка от уведомлений
			</AlertDialog.Title>
			<AlertDialog.Description>
				Хочешь отписаться от уведомлений о выступлении <strong class="text-foreground"
					>{event.title}</strong
				>?
			</AlertDialog.Description>
		</AlertDialog.Header>

		{#if formError}
			<Alert.Root variant="destructive">
				<Alert.Description>{formError}</Alert.Description>
			</Alert.Root>
		{/if}

		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<Button
				type="button"
				variant="destructive"
				onclick={handleUnsubscribe}
				disabled={unsubscribeMutation.isPending}>Отписаться</Button
			>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
