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
		event: ScheduleEventWithSubscription;
		onclose: () => void;
	}
	let { event, onclose }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The toast lives here, not in `mutate()`'s callbacks: those are dropped if the
	// dialog is dismissed while the request is in flight, which would lose the
	// confirmation of a subscription that was in fact removed.
	const unsubscribeMutation = createMutation(() => ({
		...deleteSubscriptionMutation(),
		onSuccess: () => {
			toastService.add('Подписка на уведомления отключена', 'success');
			return queryClient.invalidateQueries({ queryKey: getSubscriptionsQueryKey() });
		}
	}));

	let formError = $state('');

	function handleUnsubscribe() {
		if (!event.user_subscription) {
			onclose();
			return;
		}

		formError = '';
		unsubscribeMutation.mutate(
			{ path: { subscription_id: event.user_subscription.id } },
			{
				onSuccess: onclose,
				onError: (error) => {
					formError = getApiErrorDetail(error) ?? 'Не удалось отключить уведомления';
				}
			}
		);
	}
</script>

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
